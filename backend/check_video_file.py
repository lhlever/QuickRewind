#!/usr/bin/env python3
"""
检查视频文件是否有效，并获取详细信息
用于调试视频流格式错误问题
"""

import os
import sys
import mimetypes
import json

def check_video_file(file_path):
    """检查视频文件的有效性和详细信息"""
    result = {
        "file_path": file_path,
        "exists": False,
        "is_file": False,
        "file_size": 0,
        "file_extension": "",
        "mime_type": None,
        "is_video": False,
        "header_bytes": None,
        "file_signature": None,
        "issues": []
    }
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        result["issues"].append("文件不存在")
        return result
    
    result["exists"] = True
    
    # 检查是否为文件
    if not os.path.isfile(file_path):
        result["issues"].append("路径不是一个文件")
        return result
    
    result["is_file"] = True
    
    # 获取文件大小
    try:
        result["file_size"] = os.path.getsize(file_path)
    except Exception as e:
        result["issues"].append(f"无法获取文件大小: {str(e)}")
    
    # 获取文件扩展名
    _, result["file_extension"] = os.path.splitext(file_path)
    result["file_extension"] = result["file_extension"].lower()
    
    # 尝试使用mimetypes检测MIME类型
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        result["mime_type"] = mime_type
        result["is_video"] = mime_type is not None and mime_type.startswith("video/")
    except Exception as e:
        result["issues"].append(f"MIME类型检测失败: {str(e)}")
    
    # 读取文件头进行签名检查
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)  # 读取前16个字节
            result["header_bytes"] = header.hex()
            
            # 检查常见视频文件签名
            # MP4: 66747970 (ftyp)
            # WebM: 1a45dfa3
            # AVI: 52494646 (RIFF) 后跟着 41564920 (AVI)
            # MOV: 66747970 (ftyp) 或 52494646 (RIFF)
            # MKV: 1a45dfa3
            
            # 检查是否包含常见视频文件签名
            if b'ftyp' in header:
                result["file_signature"] = "可能是 MP4/MOV 文件 (包含ftyp)"
            elif header.startswith(b'\x1a\x45\xdf\xa3'):
                result["file_signature"] = "可能是 WebM/MKV 文件"
            elif header.startswith(b'RIFF') and b'AVI' in header[4:]:
                result["file_signature"] = "可能是 AVI 文件"
            else:
                result["issues"].append("未检测到常见视频文件签名")
                
    except Exception as e:
        result["issues"].append(f"读取文件头失败: {str(e)}")
    
    return result

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python check_video_file.py <视频文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"开始检查视频文件: {file_path}")
    result = check_video_file(file_path)
    
    # 格式化输出结果
    print("\n检查结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 输出总结
    print("\n总结:")
    if result["exists"] and result["is_file"]:
        print(f"✓ 文件存在且可访问")
        print(f"✓ 文件大小: {result['file_size']:,} 字节")
        print(f"✓ 文件扩展名: {result['file_extension']}")
        print(f"✓ 检测到的MIME类型: {result['mime_type']}")
        if result["file_signature"]:
            print(f"✓ 文件签名: {result['file_signature']}")
        
        if result["is_video"]:
            print("✓ 文件被识别为视频类型")
        else:
            print("✗ 警告: 文件未被识别为视频类型")
    
    if result["issues"]:
        print("\n发现的问题:")
        for issue in result["issues"]:
            print(f"- {issue}")
    else:
        print("\n未发现问题，文件可能有效")
    
    # 提供建议
    print("\n建议:")
    if not result["is_video"] or result["issues"]:
        print("1. 确认文件是否为有效的视频文件")
        print("2. 尝试使用视频转换工具将文件转换为标准格式(如MP4)")
        print("3. 检查文件是否完整，没有损坏")
        print("4. 确保文件权限正确，可被应用读取")
    
    print("\n调试完成")

if __name__ == "__main__":
    main()