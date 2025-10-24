import os
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# 单独检查每个依赖项的可用性
# 首先检查PyTorch
HAS_TORCH = False
try:
    import torch
    HAS_TORCH = True
    logger.info("PyTorch 已安装")
except ImportError:
    logger.warning("PyTorch 未安装")

# 检查CUDA可用性（如果PyTorch已安装）
HAS_CUDA = False
if HAS_TORCH:
    try:
        HAS_CUDA = torch.cuda.is_available()
        logger.info(f"CUDA 可用性: {HAS_CUDA}")
    except Exception:
        logger.warning("无法检查CUDA可用性")

# 检查FunASR（不需要PyTorch也可以尝试导入）
HAS_FUNASR = False
try:
    from funasr import AutoModel
    HAS_FUNASR = True
    logger.info("FunASR 已安装")
except ImportError as e:
    logger.warning(f"FunASR 导入失败: {str(e)}")

# 记录整体依赖状态
if HAS_TORCH and HAS_FUNASR:
    logger.info("语音识别所需的依赖已完全安装")
elif not HAS_TORCH:
    logger.warning("PyTorch 未安装，语音识别功能可能受限或使用替代方案")
elif not HAS_FUNASR:
    logger.warning("FunASR 未安装，语音识别功能将使用替代方案")


class SpeechRecognizer:
    """语音识别服务，基于阿里FunASR（可选依赖）"""
    
    def __init__(self, model_name: str = "paraformer-zh",
                 vad_model: str = "fsmn-vad",
                 punc_model: str = "ct-punc"):
        self.model = None
        self.model_name = model_name
        self.vad_model = vad_model
        self.punc_model = punc_model
        self._load_model()
    
    def _load_model(self):
        """加载语音识别模型"""
        if not HAS_FUNASR:
            logger.warning("无法加载FunASR模型，因为依赖未安装")
            return
            
        try:
            logger.info(f"开始加载FunASR模型: {self.model_name}")
            start_time = time.time()
            
            # 加载模型 - 使用官方推荐的方式
            self.model = AutoModel(
                model=self.model_name,
                vad_model=self.vad_model,
                punc_model=self.punc_model
                # spk_model="cam++"  # 根据需要可以启用说话人模型
            )
            
            # 如果有CUDA，将模型移至GPU
            if HAS_CUDA and self.model:
                # 注意：这里需要根据FunASR的具体API进行调整
                # 不同模型可能有不同的移动到GPU的方法
                logger.info("将模型移至GPU")
            
            load_time = time.time() - start_time
            logger.info(f"FunASR模型加载完成，耗时: {load_time:.2f}秒")
        except Exception as e:
            logger.error(f"加载FunASR模型失败: {str(e)}")
            self.model = None
    
    def transcribe(self, audio_path: str, batch_size_s: int = 300,
                   output_dir: Optional[str] = None) -> Dict[str, Any]:
        """执行语音识别
        
        Args:
            audio_path: 音频文件路径
            batch_size_s: 批处理大小（秒）
            output_dir: 输出目录
            
        Returns:
            识别结果，包含原始文本和时间戳信息
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        if not self.model:
            # 如果模型未加载，提供一个简单的替代实现
            logger.warning("使用替代的语音识别方案，因为主模型未加载")
            return self._fallback_transcribe(audio_path)
        
        try:
            logger.info(f"开始处理音频文件: {audio_path}")
            start_time = time.time()
            
            # 执行识别 - 使用官方推荐的参数
            result = self.model.generate(
                input=audio_path,
                batch_size_s=batch_size_s,
                hotword='',  # 可以根据需要设置热词
                # output_dir=output_dir  # 根据FunASR版本决定是否需要
            )
            
            process_time = time.time() - start_time
            logger.info(f"语音识别完成，耗时: {process_time:.2f}秒")
            
            # 处理结果
            return self._process_result(result)
        except Exception as e:
            logger.error(f"语音识别失败: {str(e)}")
            # 失败时使用回退方案
            return self._fallback_transcribe(audio_path)
    
    def _fallback_transcribe(self, audio_path: str) -> Dict[str, Any]:
        """回退的语音识别方案（当主模型不可用时）
        
        这个方法提供一个简单的实现，可以根据需要扩展为调用其他API或服务
        """
        logger.info(f"使用回退方案处理音频: {audio_path}")
        
        # 这里可以实现一个简单的替代方案
        # 例如调用外部API或使用更轻量级的模型
        # 目前返回一个模拟结果
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
        
        return {
            "text": f"[暂未识别] 音频文件大小: {file_size:.2f}MB",
            "segments": [
                {
                    "text": "[语音识别服务不可用，请安装PyTorch和FunASR依赖]",
                    "start_time": 0.0,
                    "end_time": 10.0,
                    "confidence": 0.0
                }
            ],
            "total_segments": 1,
            "warning": "语音识别服务不可用，请安装PyTorch和FunASR依赖"
        }
    
    def _process_result(self, raw_result: Any) -> Dict[str, Any]:
        """处理识别结果
        
        Args:
            raw_result: 原始识别结果
            
        Returns:
            结构化的识别结果
        """
        try:
            # FunASR的输出格式可能因模型而异，这里做通用处理
            transcript_segments = []
            full_text = ""
            
            # 解析结果
            if isinstance(raw_result, list):
                for item in raw_result:
                    if isinstance(item, dict):
                        # 假设item包含text、start、end等字段
                        segment = {
                            "text": item.get("text", ""),
                            "start_time": item.get("start", 0.0),
                            "end_time": item.get("end", 0.0),
                            "confidence": item.get("score", 1.0)
                        }
                        transcript_segments.append(segment)
                        full_text += segment["text"] + " "
            
            # 如果无法解析结构化数据，尝试获取纯文本
            if not transcript_segments and isinstance(raw_result, dict):
                if "text" in raw_result:
                    full_text = raw_result["text"]
                    transcript_segments = [{"text": full_text, "start_time": 0.0, "end_time": 0.0, "confidence": 1.0}]
            
            return {
                "text": full_text.strip(),
                "segments": transcript_segments,
                "total_segments": len(transcript_segments)
            }
        except Exception as e:
            logger.error(f"处理识别结果失败: {str(e)}")
            # 返回错误信息
            return {
                "text": "",
                "segments": [],
                "total_segments": 0,
                "error": str(e)
            }
    
    def generate_srt(self, recognition_result: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """生成SRT格式字幕
        
        Args:
            recognition_result: 识别结果
            output_path: 输出文件路径，如果为None则只返回内容
            
        Returns:
            SRT格式的字幕内容
        """
        srt_lines = []
        index = 1
        
        # 从识别结果中获取段落
        segments = recognition_result.get("segments", [])
        
        for segment in segments:
            start_time = segment.get("start_time", 0.0)
            end_time = segment.get("end_time", 0.0)
            text = segment.get("text", "")
            
            # 格式化时间戳
            start_str = self._format_time(start_time)
            end_str = self._format_time(end_time)
            
            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(text)
            srt_lines.append("")
            index += 1
        
        # 生成SRT内容
        srt_content = "\n".join(srt_lines)
        
        # 如果指定了输出路径，保存到文件
        if output_path:
            try:
                # 确保目录存在
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                # 写入文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                logger.info(f"SRT文件已保存: {output_path}")
            except Exception as e:
                logger.error(f"保存SRT文件失败: {str(e)}")
                raise
        
        return srt_content
    
    def _format_time(self, seconds: float) -> str:
        """将秒转换为SRT时间格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT格式的时间字符串 (HH:MM:SS,mmm)
        """
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def batch_transcribe(self, audio_paths: List[str], **kwargs) -> Dict[str, Dict[str, Any]]:
        """批量处理多个音频文件
        
        Args:
            audio_paths: 音频文件路径列表
            **kwargs: 传递给transcribe方法的参数
            
        Returns:
            字典，键为文件路径，值为识别结果
        """
        results = {}
        
        for audio_path in audio_paths:
            try:
                results[audio_path] = self.transcribe(audio_path, **kwargs)
            except Exception as e:
                logger.error(f"处理文件 {audio_path} 失败: {str(e)}")
                results[audio_path] = {"error": str(e)}
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息和依赖状态"""
        return {
            "model_name": self.model_name if self.model else "not loaded",
            "vad_model": self.vad_model,
            "punc_model": self.punc_model,
            "has_torch": HAS_TORCH,
            "has_cuda": HAS_CUDA,
            "has_funasr": HAS_FUNASR,
            "model_loaded": self.model is not None
        }


# 创建全局语音识别服务实例
speech_recognizer = SpeechRecognizer()