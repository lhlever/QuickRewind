import os
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# 从应用配置中导入设置
from app.core.config import settings

# 语音识别引擎配置
class SpeechRecognitionConfig:
    """语音识别配置类 - 从应用设置中获取配置"""
    @classmethod
    def get_config(cls):
        """获取配置字典"""
        return {
            "engine": settings.speech_engine,
            "funasr": {
                "model_name": settings.funasr_model_name,
                "vad_model": settings.funasr_vad_model,
                "punc_model": settings.funasr_punc_model
            },
            "whisper": {
                "model": settings.whisper_model,
                "language": settings.whisper_language,
                "device": settings.whisper_device
            }
        }
    
    @classmethod
    def get_engine(cls):
        """获取引擎类型"""
        return settings.speech_engine.lower()
    
    @classmethod
    def get_funasr_config(cls):
        """获取FunASR配置"""
        return {
            "model_name": settings.funasr_model_name,
            "vad_model": settings.funasr_vad_model,
            "punc_model": settings.funasr_punc_model
        }
    
    @classmethod
    def get_whisper_config(cls):
        """获取Whisper配置"""
        return {
            "model": settings.whisper_model,
            "language": settings.whisper_language,
            "device": settings.whisper_device
        }

# 打印当前配置
logger.info(f"语音识别配置: {SpeechRecognitionConfig.get_config()}")

# 检查依赖项
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
        # 自动设置设备
        if HAS_CUDA and settings.whisper_device == "cpu":
            settings.whisper_device = "cuda"
            logger.info("自动切换到CUDA设备")
    except Exception:
        logger.warning("无法检查CUDA可用性")

# 检查FunASR
HAS_FUNASR = False
try:
    from funasr import AutoModel
    HAS_FUNASR = True
    logger.info("FunASR 已安装")
except ImportError as e:
    logger.warning(f"FunASR 导入失败: {str(e)}")

# 检查Whisper
HAS_WHISPER = False
try:
    import whisper
    HAS_WHISPER = True
    logger.info("Whisper 已安装")
except ImportError as e:
    logger.warning(f"Whisper 导入失败: {str(e)}")

# 记录依赖状态
logger.info(f"语音识别依赖状态 - PyTorch: {HAS_TORCH}, CUDA: {HAS_CUDA}, FunASR: {HAS_FUNASR}, Whisper: {HAS_WHISPER}")


class SpeechRecognizer:
    """语音识别服务，支持FunASR和Whisper两种引擎"""
    
    def __init__(self, engine: str = None,
                 model_name: str = None,
                 **kwargs):
        """
        初始化语音识别器
        
        Args:
            engine: 引擎类型 ('funasr' 或 'whisper')，None则使用配置文件中的设置
            model_name: 模型名称，None则使用配置文件中的设置
            **kwargs: 其他配置参数
        """
        # 使用传入的引擎或配置文件中的引擎
        self.engine = engine.lower() if engine else SpeechRecognitionConfig.get_engine()
        
        # 模型和配置
        self.model = None
        self.model_type = "none"
        
        # 加载相应引擎
        if self.engine == "whisper":
            whisper_config = SpeechRecognitionConfig.get_whisper_config()
            self.model_name = model_name or whisper_config["model"]
            self.language = kwargs.get("language", whisper_config["language"])
            self.device = kwargs.get("device", whisper_config["device"])
            self._load_whisper_model()
        else:  # 默认使用funasr
            funasr_config = SpeechRecognitionConfig.get_funasr_config()
            self.model_name = model_name or funasr_config["model_name"]
            self.vad_model = kwargs.get("vad_model", funasr_config["vad_model"])
            self.punc_model = kwargs.get("punc_model", funasr_config["punc_model"])
            self._load_funasr_model()
        
        logger.info(f"语音识别器初始化完成，引擎: {self.engine}，模型: {self.model_name}")
    
    def _load_funasr_model(self):
        """加载FunASR语音识别模型"""
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
            
            self.model_type = "funasr"
            load_time = time.time() - start_time
            logger.info(f"FunASR模型加载完成，耗时: {load_time:.2f}秒")
        except Exception as e:
            logger.error(f"加载FunASR模型失败: {str(e)}")
            self.model = None
    
    def _load_whisper_model(self):
        """加载Whisper语音识别模型"""
        if not HAS_WHISPER:
            logger.warning("无法加载Whisper模型，因为依赖未安装")
            return
            
        try:
            logger.info(f"开始加载Whisper模型: {self.model_name}")
            start_time = time.time()
            
            # 加载Whisper模型
            self.model = whisper.load_model(
                name=self.model_name,
                device=self.device
            )
            
            self.model_type = "whisper"
            load_time = time.time() - start_time
            logger.info(f"Whisper模型加载完成，耗时: {load_time:.2f}秒")
        except Exception as e:
            logger.error(f"加载Whisper模型失败: {str(e)}")
            self.model = None
    
    def switch_engine(self, engine: str, model_name: str = None, **kwargs):
        """
        切换语音识别引擎
        
        Args:
            engine: 新的引擎类型 ('funasr' 或 'whisper')
            model_name: 新的模型名称，None则使用默认配置
            **kwargs: 其他配置参数
        """
        logger.info(f"切换引擎从 {self.engine} 到 {engine}")
        self.engine = engine.lower()
        self.model = None
        
        if self.engine == "whisper":
            whisper_config = SpeechRecognitionConfig.get_whisper_config()
            self.model_name = model_name or whisper_config["model"]
            self.language = kwargs.get("language", whisper_config["language"])
            self.device = kwargs.get("device", whisper_config["device"])
            self._load_whisper_model()
        else:  # 默认使用funasr
            funasr_config = SpeechRecognitionConfig.get_funasr_config()
            self.model_name = model_name or funasr_config["model_name"]
            self.vad_model = kwargs.get("vad_model", funasr_config["vad_model"])
            self.punc_model = kwargs.get("punc_model", funasr_config["punc_model"])
            self._load_funasr_model()
    
    def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """执行语音识别
        
        Args:
            audio_path: 音频文件路径
            **kwargs: 其他参数，根据引擎类型不同而不同
                - FunASR参数: batch_size_s, hotword, output_dir
                - Whisper参数: language, temperature, task (transcribe/translate)
        
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
            logger.info(f"开始处理音频文件: {audio_path} (引擎: {self.engine})")
            start_time = time.time()
            
            if self.engine == "whisper" and self.model_type == "whisper":
                # 使用Whisper进行识别
                result = self._transcribe_with_whisper(audio_path, **kwargs)
            else:
                # 使用FunASR进行识别
                result = self._transcribe_with_funasr(audio_path, **kwargs)
            
            process_time = time.time() - start_time
            logger.info(f"语音识别完成，耗时: {process_time:.2f}秒")
            
            return result
        except Exception as e:
            logger.error(f"语音识别失败: {str(e)}")
            # 失败时使用回退方案
            return self._fallback_transcribe(audio_path)
    
    def _transcribe_with_funasr(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """使用FunASR执行语音识别"""
        batch_size_s = kwargs.get("batch_size_s", 300)
        hotword = kwargs.get("hotword", "")
        output_dir = kwargs.get("output_dir", None)
        
        # 执行识别 - 使用官方推荐的参数
        result = self.model.generate(
            input=audio_path,
            batch_size_s=batch_size_s,
            hotword=hotword,
            # output_dir=output_dir  # 根据FunASR版本决定是否需要
        )
        
        # 处理结果
        return self._process_funasr_result(result)
    
    def _transcribe_with_whisper(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """使用Whisper执行语音识别"""
        language = kwargs.get("language", self.language)
        temperature = kwargs.get("temperature", 0.0)
        task = kwargs.get("task", "transcribe")  # transcribe 或 translate
        
        # 执行Whisper识别
        result = self.model.transcribe(
            audio_path,
            language=language,
            temperature=temperature,
            task=task
        )
        
        # 处理结果
        return self._process_whisper_result(result)
    
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
    
    def _process_funasr_result(self, raw_result: Any) -> Dict[str, Any]:
        """处理FunASR识别结果
        
        Args:
            raw_result: FunASR的原始识别结果
            
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
                "total_segments": len(transcript_segments),
                "engine": "funasr",
                "model": self.model_name
            }
        except Exception as e:
            logger.error(f"处理FunASR识别结果失败: {str(e)}")
            return {
                "text": "",
                "segments": [],
                "total_segments": 0,
                "error": str(e)
            }
    
    def _process_whisper_result(self, raw_result: Any) -> Dict[str, Any]:
        """处理Whisper识别结果
        
        Args:
            raw_result: Whisper的原始识别结果
            
        Returns:
            结构化的识别结果
        """
        try:
            # Whisper的结果格式相对固定
            transcript_segments = []
            full_text = raw_result.get("text", "").strip()
            
            # 处理时间戳和段落
            for segment in raw_result.get("segments", []):
                segment_info = {
                    "text": segment.get("text", "").strip(),
                    "start_time": segment.get("start", 0.0),
                    "end_time": segment.get("end", 0.0),
                    "confidence": segment.get("confidence", 0.0) if "confidence" in segment else 1.0
                }
                transcript_segments.append(segment_info)
            
            return {
                "text": full_text,
                "segments": transcript_segments,
                "total_segments": len(transcript_segments),
                "engine": "whisper",
                "model": self.model_name,
                "language": raw_result.get("language", self.language)
            }
        except Exception as e:
            logger.error(f"处理Whisper识别结果失败: {str(e)}")
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
        info = {
            "engine": self.engine,
            "model_name": self.model_name if self.model else "not loaded",
            "model_loaded": self.model is not None,
            "has_torch": HAS_TORCH,
            "has_cuda": HAS_CUDA,
            "has_funasr": HAS_FUNASR,
            "has_whisper": HAS_WHISPER,
            "config": SpeechRecognitionConfig.get_config()
        }
        
        # 添加引擎特定信息
        if self.engine == "funasr":
            info.update({
                "vad_model": self.vad_model,
                "punc_model": self.punc_model
            })
        else:
            info.update({
                "language": self.language,
                "device": self.device
            })
        
        return info


# 创建全局语音识别服务实例
speech_recognizer = SpeechRecognizer()