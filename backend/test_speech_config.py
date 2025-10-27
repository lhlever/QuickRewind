#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别配置测试脚本

此脚本用于测试语音识别功能的配置选项，包括引擎选择和模型大小配置。
使用方法：python test_speech_config.py [音频文件路径] [引擎类型] [模型名称]
"""

import os
import sys
import json
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.services.speech_recognition import SpeechRecognizer, SpeechRecognitionConfig
    logger.info("成功导入语音识别模块")
except ImportError as e:
    logger.error(f"导入语音识别模块失败: {str(e)}")
    sys.exit(1)


def test_speech_recognition(audio_path, engine=None, model_name=None):
    """测试语音识别功能"""
    # 验证音频文件存在
    if not os.path.exists(audio_path):
        logger.error(f"音频文件不存在: {audio_path}")
        return False
    
    logger.info(f"准备测试语音识别 - 引擎: {engine or '默认'}, 模型: {model_name or '默认'}")
    
    try:
        # 创建识别器实例
        recognizer = SpeechRecognizer(engine=engine, model_name=model_name)
        
        # 打印模型信息
        model_info = recognizer.get_model_info()
        logger.info(f"模型信息: {json.dumps(model_info, ensure_ascii=False, indent=2)}")
        
        # 执行识别
        logger.info(f"开始识别音频文件: {audio_path}")
        result = recognizer.transcribe(audio_path)
        
        # 打印结果
        logger.info(f"识别成功! 文本长度: {len(result.get('text', ''))} 字符")
        logger.info(f"识别结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 生成SRT字幕
        if result.get('segments'):
            srt_content = recognizer.generate_srt(result)
            logger.info(f"生成SRT字幕成功，包含 {result.get('total_segments', 0)} 个段落")
            
            # 保存SRT文件
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            engine_name = engine or SpeechRecognitionConfig.ENGINE
            model_size = model_name or getattr(SpeechRecognitionConfig, f"{engine_name.upper()}_MODEL_NAME" if engine_name == "funasr" else f"{engine_name.upper()}_MODEL")
            srt_path = f"{base_name}_{engine_name}_{model_size}.srt"
            
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            logger.info(f"SRT字幕已保存至: {srt_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"语音识别测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_engine_switching():
    """测试引擎切换功能"""
    logger.info("测试引擎切换功能")
    
    try:
        # 创建默认识别器
        recognizer = SpeechRecognizer()
        logger.info(f"初始引擎: {recognizer.engine}, 模型: {recognizer.model_name}")
        
        # 切换到另一个引擎
        other_engine = "whisper" if recognizer.engine == "funasr" else "funasr"
        logger.info(f"切换到引擎: {other_engine}")
        recognizer.switch_engine(other_engine)
        logger.info(f"切换后引擎: {recognizer.engine}, 模型: {recognizer.model_name}")
        
        logger.info("引擎切换测试成功")
        return True
        
    except Exception as e:
        logger.error(f"引擎切换测试失败: {str(e)}")
        return False


def main():
    """主函数"""
    # 打印当前配置
    logger.info(f"当前语音识别配置: {json.dumps(SpeechRecognitionConfig.get_config(), ensure_ascii=False, indent=2)}")
    
    # 测试引擎切换
    test_engine_switching()
    
    # 检查是否提供了音频文件路径
    if len(sys.argv) < 2:
        logger.warning("未提供音频文件路径，仅测试配置和引擎切换功能")
        logger.info("使用方法: python test_speech_config.py [音频文件路径] [引擎类型] [模型名称]")
        logger.info("引擎类型可选值: whisper, funasr")
        logger.info("模型名称:")
        logger.info("  - Whisper: tiny, base, small, medium, large")
        logger.info("  - FunASR: paraformer-zh (默认)")
        return
    
    # 获取参数
    audio_path = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else None
    model_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 验证引擎参数
    if engine and engine.lower() not in ['whisper', 'funasr']:
        logger.error(f"无效的引擎类型: {engine}，请使用 'whisper' 或 'funasr'")
        return
    
    # 执行测试
    test_speech_recognition(audio_path, engine, model_name)
    
    # 如果只测试了一个引擎，询问是否测试另一个
    if engine:
        other_engine = "whisper" if engine.lower() == "funasr" else "funasr"
        print(f"\n是否要测试另一个引擎 {other_engine}? (y/n)")
        if input().lower() == 'y':
            test_speech_recognition(audio_path, other_engine)


if __name__ == "__main__":
    main()