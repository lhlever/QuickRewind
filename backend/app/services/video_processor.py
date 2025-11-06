import os
import uuid
import ffmpeg
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from app.core.config import settings
import tempfile
import shutil
import re

logger = logging.getLogger(__name__)

# 尝试导入PyTorch，但如果失败也不中断程序
try:
    import torch
    HAS_TORCH = True
    logger.info("PyTorch 已安装")
    # 检查CUDA可用性
    HAS_CUDA = torch.cuda.is_available()
    logger.info(f"CUDA 可用性: {HAS_CUDA}")
except ImportError:
    HAS_TORCH = False
    HAS_CUDA = False
    logger.warning("PyTorch 未安装，某些高级视频处理功能将不可用")


class VideoProcessor:
    """视频处理服务"""
    
    def __init__(self):
        self.video_dir = settings.video_dir
        self.audio_dir = settings.audio_dir
        self.hls_dir = os.path.join(self.video_dir, 'hls')  # HLS文件存储目录
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        Path(self.video_dir).mkdir(parents=True, exist_ok=True)
        Path(self.audio_dir).mkdir(parents=True, exist_ok=True)
        Path(self.hls_dir).mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_video(self, file_obj, filename: str) -> Dict[str, Any]:
        """保存上传的视频文件并转换为HLS格式
        
        Args:
            file_obj: 文件对象
            filename: 原始文件名
            
        Returns:
            包含文件信息的字典
        """
        try:
            # 验证文件扩展名
            valid_extensions = ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv', '.wmv', '.mpeg', '.mpg', '.ogg']
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in valid_extensions:
                raise ValueError(f"请上传有效的视频文件，支持的格式: {', '.join(valid_extensions)}")
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(self.video_dir, unique_filename)
            
            # 保存文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file_obj, buffer)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 验证文件大小
            if file_size > settings.max_video_size:
                os.remove(file_path)
                raise ValueError(f"视频文件过大，最大支持 {settings.max_video_size / (1024*1024*1024):.1f}GB")
            
            # 尝试验证文件是否为有效的视频文件
            try:
                # 使用ffmpeg验证文件格式
                probe = ffmpeg.probe(file_path)
                # 检查是否包含视频流
                has_video_stream = any(stream["codec_type"] == "video" for stream in probe["streams"])
                if not has_video_stream:
                    os.remove(file_path)
                    raise ValueError("请上传有效的视频文件，文件不包含视频流")
            except ffmpeg.Error as e:
                os.remove(file_path)
                raise ValueError(f"请上传有效的视频文件: {e.stderr.decode()}")
            
            logger.info(f"视频文件已保存: {file_path}, 大小: {file_size / (1024*1024):.2f}MB")
            
            result = {
                "file_path": file_path,
                "filename": filename,
                "unique_filename": unique_filename,
                "file_size": file_size,
                "has_torch": HAS_TORCH,
                "has_cuda": HAS_CUDA
            }
            
            return result
        except Exception as e:
            logger.error(f"保存视频文件失败: {str(e)}")
            raise
    
    def extract_audio(self, video_path: str, output_format: str = "wav") -> str:
        """从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_format: 输出音频格式
            
        Returns:
            提取的音频文件路径
        """
        try:
            # 生成音频文件名
            video_basename = os.path.basename(video_path)
            audio_filename = f"{os.path.splitext(video_basename)[0]}_audio.{output_format}"
            audio_path = os.path.join(self.audio_dir, audio_filename)
            
            # 使用ffmpeg提取音频
            ffmpeg.input(video_path).output(
                audio_path,
                acodec="pcm_s16le",  # 无损PCM编码
                ac=1,  # 单声道
                ar="16000",  # 16kHz采样率
                loglevel="error"
            ).run(capture_stdout=True, capture_stderr=True)
            
            logger.info(f"音频提取完成: {audio_path}")
            return audio_path
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg错误: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"提取音频失败: {str(e)}")
            raise
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
            audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
            
            info = {
                "format": probe["format"].get("format_name", "unknown"),
                "duration": float(probe["format"].get("duration", 0)),
                "size": int(probe["format"].get("size", 0)),
                "bit_rate": int(probe["format"].get("bit_rate", 0)),
                "has_torch": HAS_TORCH,
                "has_cuda": HAS_CUDA
            }
            
            if video_stream:
                info["video"] = {
                    "codec": video_stream.get("codec_name", "unknown"),
                    "width": int(video_stream.get("width", 0)),
                    "height": int(video_stream.get("height", 0)),
                    "fps": eval(video_stream.get("avg_frame_rate", "0/1"))
                }
            
            if audio_stream:
                info["audio"] = {
                    "codec": audio_stream.get("codec_name", "unknown"),
                    "channels": int(audio_stream.get("channels", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 0))
                }
            
            logger.info(f"获取视频信息成功: {video_path}")
            return info
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg错误: {e.stderr.decode()}")
            # 返回基本信息，而不是抛出异常
            basic_info = {
                "format": "unknown",
                "duration": 0,
                "size": os.path.getsize(video_path) if os.path.exists(video_path) else 0,
                "bit_rate": 0,
                "has_torch": HAS_TORCH,
                "has_cuda": HAS_CUDA,
                "error": f"FFmpeg错误: {e.stderr.decode()}"
            }
            return basic_info
        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")
            # 返回基本信息，而不是抛出异常
            basic_info = {
                "format": "unknown",
                "duration": 0,
                "size": os.path.getsize(video_path) if os.path.exists(video_path) else 0,
                "bit_rate": 0,
                "has_torch": HAS_TORCH,
                "has_cuda": HAS_CUDA,
                "error": str(e)
            }
            return basic_info
    
    def extract_frames(self, video_path: str, output_dir: Optional[str] = None, 
                      interval: int = 10, max_frames: int = 50) -> List[str]:
        """提取视频帧
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录，如果为None则使用临时目录
            interval: 帧提取间隔（秒）
            max_frames: 最大提取帧数
            
        Returns:
            提取的帧文件路径列表
        """
        try:
            # 确定输出目录
            if not output_dir:
                output_dir = tempfile.mkdtemp(prefix="video_frames_")
            else:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 生成输出模式
            video_basename = os.path.splitext(os.path.basename(video_path))[0]
            output_pattern = os.path.join(output_dir, f"{video_basename}_frame_%06d.jpg")
            
            # 使用ffmpeg提取帧
            ffmpeg.input(video_path, ss=0, r=f"1/{interval}").output(
                output_pattern,
                vframes=max_frames,
                qscale=2,  # 图像质量，1-31，越小质量越好
                loglevel="error"
            ).run(capture_stdout=True, capture_stderr=True)
            
            # 获取生成的文件列表
            frame_files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) 
                                if f.startswith(f"{video_basename}_frame_")])
            
            logger.info(f"成功提取 {len(frame_files)} 帧到目录: {output_dir}")
            return frame_files
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg错误: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"提取视频帧失败: {str(e)}")
            raise
    
    def transcode_video(self, video_path: str, output_path: Optional[str] = None,
                       target_format: str = "mp4", crf: int = 23) -> str:
        """转码视频
        
        Args:
            video_path: 输入视频路径
            output_path: 输出视频路径
            target_format: 目标格式
            crf: 视频质量参数（0-51，越小质量越好）
            
        Returns:
            转码后的视频路径
        """
        try:
            # 确定输出路径
            if not output_path:
                video_basename = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(self.video_dir, f"{video_basename}_transcoded.{target_format}")
            
            # 转码视频
            ffmpeg.input(video_path).output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                crf=crf,
                preset="medium",
                loglevel="error"
            ).run(capture_stdout=True, capture_stderr=True)
            
            logger.info(f"视频转码完成: {output_path}")
            return output_path
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg错误: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"转码视频失败: {str(e)}")
            raise
    
    def cleanup_files(self, file_paths: List[str]):
        """清理临时文件
        
        Args:
            file_paths: 要删除的文件路径列表
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件 {file_path} 失败: {str(e)}")
    
    def convert_to_hls(self, video_path: str) -> Dict[str, Any]:
        """将视频转换为HLS格式
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            包含HLS文件信息的字典
        """
        try:
            # 生成唯一的HLS目录名
            video_basename = os.path.splitext(os.path.basename(video_path))[0]
            # 使用正则表达式清理目录名，避免特殊字符问题
            safe_dirname = re.sub(r'[^a-zA-Z0-9_-]', '_', video_basename)
            hls_output_dir = os.path.join(self.hls_dir, safe_dirname)
            
            # 创建HLS输出目录
            Path(hls_output_dir).mkdir(parents=True, exist_ok=True)
            
            # HLS播放列表路径
            playlist_path = os.path.join(hls_output_dir, 'playlist.m3u8')
            segment_path = os.path.join(hls_output_dir, 'segment_%03d.ts')
            
            # 使用ffmpeg将视频转换为HLS格式
            # 主要参数说明：
            # -hls_time: 每个分片的时长（秒）
            # -hls_list_size: 播放列表中包含的最大分片数
            # -hls_segment_filename: 分片文件名模式
            # -hls_flags: delete_segments（删除过期分片）+ append_list（追加到播放列表）
            # -vcodec: h264视频编码
            # -acodec: aac音频编码
            # -sc_threshold: 场景切换阈值（0表示禁用场景切换分割）
            (ffmpeg
                .input(video_path)
                .output(playlist_path,
                        hls_time=5,  # 减小分片间隔为5秒
                        hls_list_size=0,  # 0表示包含所有分片
                        hls_segment_filename=segment_path,
                        hls_flags='delete_segments+append_list',
                        vcodec='libx264',
                        acodec='aac',
                        sc_threshold=0,
                        preset='medium',
                        crf=23,
                        loglevel='error')
                .run(capture_stdout=True, capture_stderr=True))
            
            # 获取生成的HLS文件列表
            hls_files = []
            if os.path.exists(hls_output_dir):
                hls_files = [os.path.join(hls_output_dir, f) for f in os.listdir(hls_output_dir) 
                            if f.endswith('.ts') or f.endswith('.m3u8')]
            
            # 返回相对路径（从视频目录开始），便于前端访问
            relative_playlist_path = os.path.relpath(playlist_path, self.video_dir)
            relative_hls_files = [os.path.relpath(f, self.video_dir) for f in hls_files]
            
            logger.info(f"HLS转换完成，生成 {len(hls_files)} 个文件")
            
            return {
                "playlist_path": relative_playlist_path,
                "hls_files": relative_hls_files,
                "absolute_playlist_path": playlist_path,
                "absolute_hls_dir": hls_output_dir
            }
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg HLS转换错误: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"HLS转换失败: {str(e)}")
            raise
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息和可用资源状态
        
        Returns:
            系统信息字典
        """
        try:
            import platform
            
            # 获取CPU信息
            cpu_info = platform.processor() or "未知"
            
            # 获取内存信息
            memory_info = "未知"
            try:
                import psutil
                memory = psutil.virtual_memory()
                memory_info = f"{memory.total / (1024 ** 3):.2f} GB"
            except ImportError:
                pass
            
            return {
                "system": platform.system(),
                "version": platform.version(),
                "cpu": cpu_info,
                "memory": memory_info,
                "has_torch": HAS_TORCH,
                "has_cuda": HAS_CUDA
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            return {
                "error": str(e),
                "has_torch": HAS_TORCH,
                "has_cuda": HAS_CUDA
            }


# 创建全局视频处理服务实例
video_processor = VideoProcessor()