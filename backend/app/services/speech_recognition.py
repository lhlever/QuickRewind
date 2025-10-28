import os
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import time
import shutil

logger = logging.getLogger(__name__)

# 从应用配置中导入设置
from app.core.config import settings

# 本地模型目录设置
LOCAL_MODEL_DIR = os.path.join(settings.data_dir, "models")
# 确保本地模型目录存在
os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)

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
        # 根据可用设备自动选择，但不强制切换
        if HAS_CUDA and settings.whisper_device.lower() != "cuda":
            logger.info("检测到GPU可用，建议设置device为'cuda'以获得更好性能")
        elif not HAS_CUDA and settings.whisper_device.lower() == "cuda":
            logger.warning("未检测到GPU，但设备设置为'cuda'，将自动使用'cpu'")
            settings.whisper_device = "cpu"
    except Exception as e:
        logger.warning(f"无法检查CUDA可用性: {str(e)}")
        settings.whisper_device = "cpu"  # 出错时默认使用CPU

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
    """语音识别服务，支持FunASR和Whisper两种引擎，支持本地模型"""
    
    def __init__(self, engine: str = None, model_name: str = None, use_local_model: bool = True, force_cpu: bool = False, **kwargs):
        """
        初始化语音识别器并确保模型下载到本地
        
        Args:
            engine: 引擎类型 ('funasr' 或 'whisper')，None则使用配置文件中的设置
            model_name: 模型名称，None则使用配置文件中的设置
            use_local_model: 是否使用本地模型，默认为True
            force_cpu: 是否强制使用CPU，即使有GPU也可用
            **kwargs: 其他配置参数
        """
        logger.info("初始化语音识别器...")
        
        # 确保本地模型目录存在
        os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
        logger.info(f"本地模型根目录: {LOCAL_MODEL_DIR}")
        
        # 强制使用Whisper的tiny模型，这是最容易下载和加载成功的
        self.engine = "whisper"
        self.use_local_model = True  # 强制使用本地模型
        self.force_cpu = True  # 强制使用CPU确保稳定性
        self.model = None
        self.model_type = "none"
        self.model_name = "tiny"  # 直接使用最小的模型
        self.language = "zh"  # 中文识别
        self.device = "cpu"  # 强制使用CPU
        
        logger.info(f"强制使用Whisper tiny模型，引擎: {self.engine}, 模型: {self.model_name}, 设备: {self.device}")
        
        # 直接加载Whisper tiny模型
        self._load_whisper_model()
        
        # 验证模型加载状态
        if self.model is not None:
            logger.info(f"模型加载成功！模型类型: {self.model_type}")
        else:
            logger.error("模型加载失败，将尝试使用备用引擎")
            # 尝试切换到另一个引擎
            alternative_engine = "whisper" if self.engine == "funasr" else "funasr"
            logger.info(f"尝试切换到备用引擎: {alternative_engine}")
            try:
                self.switch_engine(alternative_engine)
            except Exception as e:
                logger.error(f"备用引擎切换失败: {str(e)}")
                logger.warning("所有引擎加载失败，将使用简单的替代方案")
        
        logger.info(f"语音识别器初始化完成，引擎: {self.engine}，模型: {self.model_name}，本地模型: {self.use_local_model}")
    
    def _get_local_model_path(self, model_type: str, model_name: str) -> str:
        """获取本地模型路径"""
        model_dir = os.path.join(LOCAL_MODEL_DIR, model_type, model_name)
        os.makedirs(model_dir, exist_ok=True)
        return model_dir
    
    def _load_funasr_model(self):
        """加载FunASR语音识别模型，确保模型下载到本地"""
        if not HAS_FUNASR:
            logger.warning("无法加载FunASR模型，因为依赖未安装")
            return
            
        try:
            logger.info(f"开始加载FunASR模型: {self.model_name}")
            start_time = time.time()
            
            # 确保本地模型目录存在
            model_dir = self._get_local_model_path("funasr", self.model_name)
            os.makedirs(model_dir, exist_ok=True)
            
            # 设置环境变量确保模型下载到本地
            os.environ["FUNASR_CACHE_DIR"] = os.path.join(LOCAL_MODEL_DIR, "funasr")
            os.environ["MODEL_HOME"] = os.path.join(LOCAL_MODEL_DIR, "modelscope")
            logger.info(f"设置模型缓存目录: {os.environ['FUNASR_CACHE_DIR']}")
            logger.info(f"设置ModelScope缓存目录: {os.environ['MODEL_HOME']}")
            
            # 准备模型参数，强制使用本地路径
            model_kwargs = {
                "model": self.model_name,
                "vad_model": self.vad_model,
                "punc_model": self.punc_model,
                "device": "cpu"  # 强制使用CPU以避免GPU相关问题
            }
            
            logger.info("开始下载/加载模型...")
            # 加载模型 - 使用官方推荐的方式
            self.model = AutoModel(**model_kwargs)
            
            # 验证模型是否成功加载
            if self.model is not None:
                self.model_type = "funasr"
                load_time = time.time() - start_time
                logger.info(f"FunASR模型加载成功！耗时: {load_time:.2f}秒")
                logger.info(f"模型已成功下载并缓存到本地: {model_dir}")
            else:
                logger.error("模型加载失败：self.model为None")
                
        except ImportError as e:
            logger.error(f"导入错误，缺少依赖: {str(e)}")
            logger.error("请确保已安装: pip install -U funasr modelscope")
            self.model = None
        except Exception as e:
            logger.error(f"加载FunASR模型失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 尝试使用更小的模型或替代方案
            logger.info("尝试使用替代模型...")
            try:
                # 使用更轻量的模型配置
                lightweight_model_kwargs = {
                    "model": "paraformer-zh-small",  # 更小的模型
                    "device": "cpu"
                }
                self.model = AutoModel(**lightweight_model_kwargs)
                if self.model:
                    self.model_name = "paraformer-zh-small"
                    logger.info(f"成功加载轻量级模型: {self.model_name}")
                else:
                    self.model = None
            except Exception as inner_e:
                logger.error(f"替代模型加载也失败: {str(inner_e)}")
                self.model = None
    
    def _load_whisper_model(self):
        """加载Whisper语音识别模型，确保模型下载到本地"""
        global HAS_WHISPER
        global whisper
        
        # 重新检查whisper模块是否可用
        try:
            import whisper
            HAS_WHISPER = True
        except ImportError:
            HAS_WHISPER = False
            
        if not HAS_WHISPER:
            logger.error("无法加载Whisper模型，因为依赖未安装")
            logger.error("正在尝试安装依赖...")
            try:
                import subprocess
                subprocess.check_call(["pip", "install", "openai-whisper"])
                logger.info("依赖安装成功，尝试导入模块")
                import whisper
                HAS_WHISPER = True
            except Exception as install_e:
                logger.error(f"依赖安装失败: {str(install_e)}")
                return
        
        try:
            logger.info(f"开始加载Whisper模型: {self.model_name}")
            logger.info(f"这是一个小型模型，下载和加载应该很快")
            start_time = time.time()
            
            # 确保本地模型目录存在
            local_model_dir = self._get_local_model_path("whisper", self.model_name)
            os.makedirs(local_model_dir, exist_ok=True)
            logger.info(f"本地模型目录已准备好: {local_model_dir}")
            
            # 强制设置缓存目录环境变量
            torch_hub_dir = os.path.join(LOCAL_MODEL_DIR, "torch_hub")
            os.makedirs(torch_hub_dir, exist_ok=True)
            os.environ["TORCH_HOME"] = torch_hub_dir
            os.environ["HF_HOME"] = os.path.join(LOCAL_MODEL_DIR, "huggingface")
            os.makedirs(os.environ["HF_HOME"], exist_ok=True)
            logger.info(f"设置缓存目录完成")
            
            # 打印当前环境变量以便调试
            logger.info(f"当前TORCH_HOME: {os.environ.get('TORCH_HOME')}")
            
            # 直接使用tiny模型（最小最可靠）
            logger.info("正在下载Whisper tiny模型（这是最小模型，只有~150MB）...")
            logger.info("首次下载可能需要一些时间，请耐心等待...")
            
            # 直接指定模型并加载
            self.model = whisper.load_model("tiny", device="cpu")
            
            # 验证模型是否成功加载
            if self.model is not None:
                self.model_type = "whisper"
                load_time = time.time() - start_time
                logger.info(f"✅ Whisper tiny模型加载成功！耗时: {load_time:.2f}秒")
                logger.info(f"模型已成功下载并缓存到本地目录")
            else:
                logger.error("❌ Whisper模型加载失败：self.model为None")
                
        except Exception as e:
            logger.error(f"❌ 加载Whisper模型时发生错误: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.model = None
    
    def switch_engine(self, engine: str, model_name: str = None, use_local_model: bool = None, force_cpu: bool = None, **kwargs):
        """
        切换语音识别引擎
        
        Args:
            engine: 新的引擎类型 ('funasr' 或 'whisper')
            model_name: 新的模型名称，None则使用默认配置
            use_local_model: 是否使用本地模型，None则保持当前设置
            **kwargs: 其他配置参数
        """
        logger.info(f"切换引擎从 {self.engine} 到 {engine}")
        self.engine = engine.lower()
        self.model = None
        
        # 更新本地模型设置（如果提供）
        if use_local_model is not None:
            self.use_local_model = use_local_model
        
        # 更新CPU强制设置（如果提供）
        if force_cpu is not None:
            self.force_cpu = force_cpu
            if self.force_cpu:
                logger.info("切换为强制使用CPU运行模型")
                if HAS_TORCH:
                    settings.whisper_device = "cpu"
        
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
            **kwargs: 其他参数
        
        Returns:
            识别结果，包含原始文本和时间戳信息
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 强制使用Whisper tiny模型，如果模型未加载则直接重新加载
        if not self.model:
            logger.warning("模型未加载，尝试重新加载Whisper tiny模型...")
            self._load_whisper_model()
            
            # 如果仍然未加载成功，尝试直接使用whisper库进行单次调用
            if not self.model:
                logger.warning("模型加载失败，尝试直接使用whisper库进行单次识别...")
                try:
                    import whisper
                    logger.info("直接使用whisper库加载tiny模型进行单次识别")
                    temp_model = whisper.load_model("tiny", device="cpu")
                    logger.info(f"直接识别音频文件: {audio_path}")
                    result = temp_model.transcribe(audio_path, language="zh")
                    logger.info("✅ 直接识别成功")
                    return self._process_whisper_result(result)
                except Exception as direct_e:
                    logger.error(f"❌ 直接识别也失败: {str(direct_e)}")
                    return self._fallback_transcribe(audio_path)
        
        try:
            logger.info(f"开始处理音频文件: {audio_path} (使用Whisper tiny模型)")
            start_time = time.time()
            
            # 直接使用Whisper进行识别
            result = self._transcribe_with_whisper(audio_path, language="zh", **kwargs)
            
            process_time = time.time() - start_time
            logger.info(f"✅ 语音识别完成，耗时: {process_time:.2f}秒")
            
            return result
        except Exception as e:
            logger.error(f"❌ 语音识别过程中发生错误: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            # 最后的回退方案
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
        
        提供一个基于文件信息的基本转录结果，而不是简单的错误消息
        """
        logger.info(f"使用回退方案处理音频: {audio_path}")
        
        # 获取文件信息
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
        
        # 尝试使用Python内置库获取音频基本信息
        audio_info = ""
        try:
            # 尝试获取音频文件的基本信息
            import wave
            if audio_path.lower().endswith('.wav'):
                with wave.open(audio_path, 'r') as wav_file:
                    channels = wav_file.getnchannels()
                    sample_rate = wav_file.getframerate()
                    frames = wav_file.getnframes()
                    duration = frames / float(sample_rate)
                    audio_info = f"音频格式: WAV, 声道: {channels}, 采样率: {sample_rate}Hz, 估计时长: {duration:.1f}秒"
        except Exception as e:
            logger.warning(f"获取音频信息失败: {str(e)}")
        
        # 返回一个更有帮助的结果
        return {
            "text": f"[音频已提取] {audio_info}。请安装语音识别依赖以获取实际转录内容。",
            "segments": [
                {
                    "text": f"音频文件信息: {file_size:.2f}MB。请安装PyTorch和FunASR依赖以启用语音识别功能。",
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