from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from app.services.video_processor import video_processor
from app.services.speech_recognition import speech_recognizer
from app.services.llm_service import llm_service
from app.core.database import get_db
from app.models.video import Video, VideoStatus
from sqlalchemy.orm import Session
import time
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["videos"])


@router.post("/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """上传视频文件"""
    try:
        # 保存视频文件
        file_info = video_processor.save_uploaded_video(file.file, file.filename)
        
        # 创建视频记录
        video = Video(
            id=uuid.uuid4(),
            filename=file_info["filename"],
            file_path=file_info["file_path"],
            file_size=file_info["file_size"],
            status=VideoStatus.UPLOADED
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        return {
            "message": "视频上传成功",
            "video_id": str(video.id),
            "filename": video.filename,
            "file_size": video.file_size
        }
    except Exception as e:
        logger.error(f"视频上传失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/videos/{video_id}")
async def get_video_info(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取视频信息"""
    try:
        # 查询视频记录
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 获取视频技术信息
        video_info = video_processor.get_video_info(video.file_path)
        
        return {
            "video_id": str(video.id),
            "filename": video.filename,
            "status": video.status.value,
            "file_size": video.file_size,
            "created_at": video.created_at.isoformat(),
            "updated_at": video.updated_at.isoformat(),
            "technical_info": video_info,
            "transcript": video.transcript,
            "summary": video.summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/videos/{video_id}/process")
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
    """视频处理后台任务"""
    try:
        # 重新获取数据库会话
        from sqlalchemy.orm import Session
        from app.core.database import SessionLocal
        db = SessionLocal()
        
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"视频不存在: {video_id}")
            return
        
        try:
            # 提取音频
            audio_path = video_processor.extract_audio(video.file_path)
            video.audio_path = audio_path
            db.commit()
            
            # 语音识别
            recognition_result = speech_recognizer.transcribe(audio_path)
            
            # 生成SRT字幕
            srt_content = speech_recognizer.generate_srt(recognition_result)
            video.transcript = recognition_result["text"]
            video.srt_content = srt_content
            
            # 更新状态
            video.status = VideoStatus.TRANSCRIBED
            db.commit()
            
            logger.info(f"视频处理完成: {video_id}")
        except Exception as e:
            # 更新为失败状态
            video.status = VideoStatus.FAILED
            video.error_message = str(e)
            db.commit()
            logger.error(f"视频处理失败: {video_id}, 错误: {str(e)}")
    finally:
        db.close()


@router.get("/videos/{video_id}/transcript")
async def get_transcript(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取视频转录文本"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript:
            raise HTTPException(status_code=400, detail="视频尚未转录")
        
        return {
            "video_id": video_id,
            "transcript": video.transcript,
            "has_srt": video.srt_content is not None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取转录文本失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/videos/{video_id}/srt")
async def get_srt(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取SRT字幕"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.srt_content:
            raise HTTPException(status_code=400, detail="SRT字幕尚未生成")
        
        return {
            "video_id": video_id,
            "srt_content": video.srt_content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取SRT字幕失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/videos/{video_id}/summarize")
async def summarize_video(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """生成视频摘要"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法生成摘要")
        
        # 生成摘要
        summary = llm_service.generate_summary(video.transcript)
        
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


@router.post("/videos/{video_id}/analyze")
async def analyze_video(video_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """分析视频内容"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法分析内容")
        
        # 分析视频内容
        analysis = llm_service.analyze_video_content(video.transcript)
        
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


@router.post("/videos/{video_id}/query")
async def query_video(
    video_id: str,
    question: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """基于视频内容回答问题"""
    try:
        # 查询视频
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        if not video.transcript:
            raise HTTPException(status_code=400, detail="视频尚未转录，无法回答问题")
        
        # 基于转录文本回答问题
        answer = llm_service.answer_question(video.transcript, question)
        
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