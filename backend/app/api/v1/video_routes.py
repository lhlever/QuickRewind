from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import threading
import os
from datetime import datetime, timezone
from app.services.video_processor import video_processor
from app.services.speech_recognition import speech_recognizer
# 提前导入llm_service，确保在使用前已定义
from app.services.llm_service import llm_service
from app.core.database import get_db, SessionLocal
from app.core.mcp import mcp_server
from app.models.video import Video, VideoStatus, VideoOutline
from sqlalchemy.orm import Session
from sqlalchemy import or_
import time
import uuid
from app.core.config import settings

# 内存中存储视频处理步骤信息，格式: {video_id: {"steps": [...], "progress": 0, "last_updated": ...}}
processing_info_cache = {}
processing_info_lock = threading.Lock()

# 处理步骤跟踪辅助函数
def initialize_processing_info(video_id: str):
    """初始化视频处理信息"""
    with processing_info_lock:
        processing_info_cache[video_id] = {
            "steps": [],
            "progress": 0,
            "last_updated": datetime.now(timezone.utc)
        }

def start_step(video_id: str, step_name: str):
    """开始一个处理步骤"""
    with processing_info_lock:
        if video_id not in processing_info_cache:
            initialize_processing_info(video_id)
        
        step = {
            "name": step_name,
            "status": "in_progress",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "duration": None
        }
        processing_info_cache[video_id]["steps"].append(step)
        processing_info_cache[video_id]["last_updated"] = datetime.now(timezone.utc)
        
        # 更新进度（基于已完成的步骤和当前步骤）
        total_steps = 4  # 上传、提取音频、语音识别和字幕生成、生成摘要、向量存储
        current_step_index = len(processing_info_cache[video_id]["steps"]) - 1
        if current_step_index >= 0:
            progress = int((current_step_index + 0.5) / total_steps * 100)  # 当前步骤完成50%
            processing_info_cache[video_id]["progress"] = min(progress, 99)
            

def complete_step(video_id: str, step_name: str):
    """完成一个处理步骤"""
    with processing_info_lock:
        if video_id in processing_info_cache:
            for step in processing_info_cache[video_id]["steps"]:
                if step["name"] == step_name and step["status"] == "in_progress":
                    start_time = datetime.fromisoformat(step["start_time"])
                    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                    step["status"] = "completed"
                    step["duration"] = duration
                    break
            
            # 更新进度
            total_steps = 4
            completed_steps = sum(1 for s in processing_info_cache[video_id]["steps"] if s["status"] == "completed")
            progress = int(completed_steps / total_steps * 100)
            processing_info_cache[video_id]["progress"] = min(progress, 99)
            processing_info_cache[video_id]["last_updated"] = datetime.now(timezone.utc)
            

def fail_step(video_id: str, step_name: str):
    """标记一个步骤失败"""
    with processing_info_lock:
        if video_id in processing_info_cache:
            for step in processing_info_cache[video_id]["steps"]:
                if step["name"] == step_name:
                    if "start_time" in step:
                        start_time = datetime.fromisoformat(step["start_time"])
                        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                        step["duration"] = duration
                    step["status"] = "failed"
                    break
            
            processing_info_cache[video_id]["last_updated"] = datetime.now(timezone.utc)
            

def get_processing_info(video_id: str):
    """获取视频处理信息"""
    with processing_info_lock:
        if video_id in processing_info_cache:
            return processing_info_cache[video_id].copy()
        return {"steps": [], "progress": 0, "last_updated": None}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """上传视频文件"""
    try:
        # 保存视频文件
        file_info = video_processor.save_uploaded_video(file.file, file.filename)
        
        # 创建视频记录
        video = Video(
            id=str(uuid.uuid4()),  # 转换为字符串以匹配数据库类型
            filename=file_info["filename"],
            filepath=file_info["file_path"],
            filesize=file_info["file_size"],
            status=VideoStatus.UPLOADING
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 上传完成后自动触发处理任务（转录和视频分析）
        video.status = VideoStatus.PROCESSING
        db.commit()
        background_tasks.add_task(_process_video_task, video.id, db)
        
        return {
            "message": "视频上传成功，正在进行转录和分析",
            "video_id": str(video.id),
            "filename": video.filename,
            "file_size": video.filesize,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"视频上传失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{video_id}")
async def get_video_info(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取视频信息"""
    try:
        # 查询视频记录 - 确保video_id是字符串类型
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 获取视频技术信息
        video_info = video_processor.get_video_info(video.filepath)
        
        return {
            "video_id": str(video.id),
            "filename": video.filename,
            "status": video.status.value,
            "file_size": video.filesize,
            "created_at": video.created_at.isoformat(),
            "updated_at": video.updated_at.isoformat() if video.updated_at else None,
            "technical_info": video_info,
            "transcript": video.transcript_text,
            "summary": video.summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{video_id}/process")
async def process_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """处理视频（提取音频、语音识别）"""
    try:
        # 查询视频记录
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 更新状态
        video.status = VideoStatus.PROCESSING
        db.commit()
        
        # 添加到后台任务
        background_tasks.add_task(_process_video_task, video_id, db)
        
        return {
            "message": "视频处理已开始",
            "video_id": video_id,
            "status": "processing"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始视频处理失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


def _process_video_task(video_id: str, db: Session):
    """视频处理后台任务 - 使用内存跟踪处理步骤"""
    try:
        # 重新获取数据库会话和必要的服务
        from sqlalchemy.orm import Session
        from app.core.database import SessionLocal
        from app.core.milvus import milvus_manager, milvus_context
        from app.core.mcp import mcp_server
        from app.services.llm_service import llm_service
        import numpy as np
        from datetime import datetime
        db = SessionLocal()
        
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"视频不存在: {video_id}")
            return
        
        # 初始化内存中的处理步骤信息
        initialize_processing_info(video_id)
        
        try:
            # 步骤1: 提取音频
            start_step(video_id, "提取音频")
            audio_path = video_processor.extract_audio(video.filepath)
            video.audio_path = audio_path
            complete_step(video_id, "提取音频")
            db.commit()
            
            # 更新状态为转录中
            video.status = VideoStatus.TRANSCRIBING
            db.commit()
            
            # 步骤2: 语音识别并生成字幕（合并为一个步骤）
            start_step(video_id, "语音识别和字幕生成")
            # 调用语音识别，同时生成并保存SRT字幕
            recognition_result = speech_recognizer.transcribe(audio_path)
            
            # 生成SRT字幕
            subtitle_path = os.path.join(settings.subtitle_dir, f"{video_id}.srt")
            srt_content = speech_recognizer.generate_srt(recognition_result, subtitle_path)
            
            # 保存转录文本和字幕路径
            video.transcript_text = recognition_result["text"]
            video.subtitle_path = subtitle_path
            
            complete_step(video_id, "语音识别和字幕生成")
            db.commit()
            
            # 更新状态为分析中
            video.status = VideoStatus.ANALYZING
            db.commit()
            
            # 步骤4: 生成视频大纲
            start_step(video_id, "生成视频大纲")
            # 读取SRT文件
            with open(video.subtitle_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # 生成大纲
            outline_data = llm_service.generate_video_outline(srt_content)
            
            # 创建VideoOutline记录
            video_outline = VideoOutline(
                id=str(uuid.uuid4()),
                video_id=video.id,
                outline_data=outline_data
            )
            db.add(video_outline)
            
            # 从大纲生成简短摘要（作为原摘要字段的替代）
            if outline_data and 'main_sections' in outline_data and outline_data['main_sections']:
                # 从大纲的章节标题和总结生成摘要
                summary_parts = []
                for section in outline_data['main_sections'][:3]:  # 只取前3个主要章节
                    if 'title' in section:
                        summary_parts.append(section['title'])
                    if 'summary' in section:
                        summary_parts.append(section['summary'])
                # 生成简短摘要
                summary = ' '.join(summary_parts)[:500]  # 限制长度
                video.summary = summary
                
            complete_step(video_id, "生成视频大纲")
            db.commit()
            
            # 步骤5: 向量存储
            start_step(video_id, "向量存储")
            try:
                # 确保llm_service导入正确
                if 'llm_service' not in globals():
                    from app.services.llm_service import llm_service
                
                # 获取视频时长
                try:
                    video_info = video_processor.get_video_info(video.filepath)
                    duration = float(video_info.get("duration", 0))
                    logger.info(f"视频时长: {duration}秒")
                except Exception as e:
                    logger.warning(f"获取视频时长失败: {str(e)}，使用默认值0")
                    duration = 0.0
                
                # 准备向量数据和元数据
                vectors = []
                metadata = []
                
                # 只为每个字幕段落生成向量，不存储整体转录和摘要的向量
                # 按照要求，只保存单个句子的向量
                if recognition_result and 'segments' in recognition_result:
                    segments = recognition_result['segments']
                    logger.info(f"开始为视频 {video_id} 的 {len(segments)} 个字幕段落生成向量")
                    
                    # 批量生成向量以提高效率
                    segment_texts = [segment.get('text', '').strip() for segment in segments]
                    segment_embeddings = llm_service.batch_generate_embeddings(segment_texts)
                    
                    # 添加每个段落的向量和元数据
                    for i, (segment, embedding) in enumerate(zip(segments, segment_embeddings)):
                        text = segment.get('text', '').strip()
                        if text:  # 只处理非空文本
                            vectors.append(np.array(embedding))
                            metadata.append({
                                "video_id": video_id,
                                "content_type": "subtitle_segment",
                                "content": text,
                                "start_time": float(segment.get('start_time', 0.0)),
                                "end_time": float(segment.get('end_time', 0.0))
                            })
                    
                    logger.info(f"成功为 {len(segments)} 个字幕段落生成向量")
                
                # 使用上下文管理器连接Milvus并插入数据
                logger.info(f"开始连接Milvus并插入数据，共 {len(vectors)} 个向量")
                with milvus_context() as mc:
                    logger.info(f"Milvus连接成功，开始插入向量数据")
                    vector_ids = mc.insert_vectors(vectors, metadata)
                    logger.info(f"成功将视频 {video_id} 的所有向量数据存入Milvus")
                    
                    # 保存向量索引信息到数据库（如果VectorIndex模型存在）
                    try:
                        from app.models.vector import VectorIndex
                        index_count = 0
                        for i, vector_id in enumerate(vector_ids):
                            vector_index = VectorIndex(
                                id=str(vector_id),
                                video_id=video_id,
                                content_type=metadata[i]["content_type"],
                                content=metadata[i]["content"],
                                start_time=metadata[i]["start_time"],
                                end_time=metadata[i]["end_time"],
                                vector_metadata="{}",
                                vector_dim=len(vectors[i])  # 使用当前向量的维度
                            )
                            db.add(vector_index)
                            index_count += 1
                        db.commit()
                        logger.info(f"成功保存 {index_count} 条向量索引信息到数据库")
                    except ImportError:
                        logger.warning("VectorIndex模型不存在，跳过向量索引信息保存")
                    except Exception as e:
                        logger.error(f"保存向量索引信息到数据库失败: {str(e)}")
                        db.rollback()
                
                # 完成向量存储步骤
                complete_step(video_id, "向量存储")
                
            except Exception as e:
                fail_step(video_id, "向量存储")
                logger.error(f"将视频 {video_id} 存入Milvus失败: {str(e)}")
                # 记录详细错误信息
                import traceback
                logger.error(f"详细错误堆栈: {traceback.format_exc()}")
                # 不中断整个处理流程，继续更新状态
            
            # 更新状态为完成
            video.status = VideoStatus.COMPLETED
            video.completed_at = datetime.utcnow()
            db.commit()
            
            # 更新进度为100%
            with processing_info_lock:
                if video_id in processing_info_cache:
                    processing_info_cache[video_id]["progress"] = 100
            
            logger.info(f"视频处理完成: {video_id}，已完成转录、分析并存入Milvus")
        except Exception as e:
            # 更新为失败状态
            video.status = VideoStatus.FAILED
            db.commit()
            logger.error(f"视频处理失败: {video_id}, 错误: {str(e)}")
            
            # 标记当前进行中的步骤为失败
            processing_info = get_processing_info(video_id)
            for step in processing_info["steps"]:
                if step["status"] == "in_progress":
                    fail_step(video_id, step["name"])
                    break
    finally:
        db.close()


@router.get("/{video_id}/transcript")
async def get_transcript(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取视频转录文本"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript_text:
            raise HTTPException(status_code=400, detail="视频尚未转录")
        
        return {
            "video_id": video_id,
            "transcript": video.transcript_text,
            "has_srt": video.subtitle_path is not None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取转录文本失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{video_id}/status")
async def get_video_processing_status(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取视频处理状态和进度信息 - 从内存中获取处理步骤"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 从内存缓存中获取处理步骤信息
        processing_info = get_processing_info(video_id)
        
        # 如果视频已经完成，但进度不是100%，则设置为100%
        if video.status == VideoStatus.COMPLETED and processing_info["progress"] < 100:
            with processing_info_lock:
                if video_id in processing_info_cache:
                    processing_info_cache[video_id]["progress"] = 100
                    processing_info["progress"] = 100
        
        # 如果视频已经失败，确保进度反映真实情况
        elif video.status == VideoStatus.FAILED:
            # 保持内存中计算的进度不变
            pass
        
        return {
            "video_id": video_id,
            "status": video.status.value,
            "progress_percentage": processing_info["progress"],
            "processing_steps": processing_info["steps"],
            "filename": video.filename,
            "created_at": video.created_at.isoformat() if video.created_at else None,
            "completed_at": video.completed_at.isoformat() if video.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频处理状态失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
#         # 查询视频
#         video = db.query(Video).filter(Video.id == video_id).first()
#         if not video:
#             raise HTTPException(status_code=404, detail="视频不存在")
#         
#         # 这里需要实现从subtitle_path读取内容的逻辑
#         # if not video.subtitle_path:
#         #     raise HTTPException(status_code=400, detail="SRT字幕尚未生成")
#         
#         return {
#             "video_id": video_id,
#             "error": "此功能暂不可用"
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"获取SRT字幕失败: {str(e)}")
#         raise HTTPException(status_code=400, detail=str(e))


@router.post("/{video_id}/summarize")
async def summarize_video(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """生成视频摘要"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript_text:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法生成摘要")
        
        # 生成摘要
        summary = llm_service.generate_summary(video.transcript_text)
        
        # 保存摘要
        video.summary = summary
        db.commit()
        
        return {
            "video_id": video_id,
            "summary": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成视频摘要失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{video_id}/analyze")
async def analyze_video(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """分析视频内容"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript_text:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法分析内容")
        
        # 分析视频内容
        analysis = llm_service.analyze_video_content(video.transcript_text)
        
        # 保存分析结果
        video.analysis_result = analysis
        db.commit()
        
        return {
            "video_id": video_id,
            "analysis": analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析视频内容失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{video_id}/query")
async def query_video(
    video_id: str,
    request: dict,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """基于视频内容回答问题"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript_text:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法回答问题")
        
        question = request.get("question", "")
        if not question:
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        # 基于转录文本回答问题
        answer = llm_service.answer_question(video.transcript_text, question)
        
        return {
            "video_id": video_id,
            "question": question,
            "answer": answer
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回答视频相关问题失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{video_id}/outline")
async def get_video_outline(
    video_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取视频大纲"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 检查是否已有VideoOutline记录
        from app.models.video import VideoOutline
        video_outline = db.query(VideoOutline).filter(VideoOutline.video_id == video_id).first()
        
        if video_outline:
            return {
                "video_id": video_id,
                "outline": video_outline.outline_data,
                "has_outline": True
            }
        
        if not video.transcript_text:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法生成大纲")
        
        # 生成大纲
        outline_data = llm_service.generate_outline(video.transcript_text)
        
        # 创建VideoOutline记录
        video_outline = VideoOutline(
            id=str(uuid.uuid4()),
            video_id=video_id,
            outline_data=outline_data
        )
        db.add(video_outline)
        db.commit()
        
        return {
            "video_id": video_id,
            "outline": outline_data,
            "has_outline": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成视频大纲失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search")
async def search_videos(
    request: dict,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """搜索视频"""
    try:
        query = request.get("query", "")
        if not query:
            return {"results": [], "total": 0}
        
        logger.info(f"开始搜索视频，查询内容: {query}")
        
        # 优先使用向量搜索（通过MCP工具）
        try:
            # 调用MCP工具进行向量搜索
            logger.info(f"调用MCP工具 search_video_by_vector 进行向量搜索")
            vector_search_response = await mcp_server.call_tool_async(
                tool_name="search_video_by_vector",
                parameters={"query": query, "top_k": 10}  # 明确指定top_k参数
            )
            
            # 添加详细的响应结构日志
            logger.info(f"向量搜索响应状态: {vector_search_response.success}")
            logger.info(f"向量搜索响应类型: {type(vector_search_response.result)}")
            if isinstance(vector_search_response.result, dict):
                logger.info(f"向量搜索响应包含字段: {list(vector_search_response.result.keys())}")
                search_results = vector_search_response.result.get("results", [])
                total = vector_search_response.result.get("total", 0)
                logger.info(f"向量搜索结果数量: {len(search_results)}, 总数: {total}")
                # 记录第一个结果的结构用于调试
                if search_results:
                    logger.info(f"第一个搜索结果的结构: {list(search_results[0].keys())}")
            
            if vector_search_response.success and isinstance(vector_search_response.result, dict):
                search_results = vector_search_response.result.get("results", [])
                total = vector_search_response.result.get("total", 0)
                logger.info(f"向量搜索完成，返回 {total} 个结果，准备返回给前端")
                
                # 确保返回的数据格式正确
                response_data = {
                    "results": search_results,
                    "total": total,
                    "search_type": "vector"
                }
                logger.info(f"最终返回给前端的数据结构: {list(response_data.keys())}")
                return response_data
            else:
                logger.warning(f"向量搜索失败或返回格式不正确，回退到简单搜索")
                logger.warning(f"向量搜索失败详情: {str(vector_search_response.error) if hasattr(vector_search_response, 'error') else '未知错误'}")
        except Exception as e:
            logger.warning(f"调用向量搜索MCP工具失败: {str(e)}，回退到简单搜索")
            import traceback
            logger.warning(f"详细错误堆栈: {traceback.format_exc()}")
        
        # 回退方案：简单数据库搜索
        conditions = [Video.filename.ilike(f"%{query}%")]
        if Video.transcript_text is not None:
            conditions.append(Video.transcript_text.ilike(f"%{query}%"))
        if Video.summary is not None:
            conditions.append(Video.summary.ilike(f"%{query}%"))
        
        videos = db.query(Video).filter(or_(*conditions)).all()
        
        # 构造响应
        results = [
            {
                "video_id": str(video.id),
                "filename": video.filename,
                "status": video.status.value,
                "summary": video.summary or "",
                "created_at": video.created_at.isoformat()
            }
            for video in videos
        ]
        
        return {
            "results": results,
            "total": len(results),
            "search_type": "simple"
        }
    except Exception as e:
        logger.error(f"搜索视频失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))