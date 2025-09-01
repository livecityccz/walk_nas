#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAS目录遍历器测试脚本
用于测试基本功能和配置
"""

import os
import sys
import json
from nas_walker import NASWalker


def test_config_loading():
    """测试配置文件加载功能"""
    print("🧪 测试配置文件加载...")
    
    try:
        walker = NASWalker()
        print("✅ 配置文件加载成功")
        print(f"   - NAS服务器: {walker.config['NAS_SERVER']['ip']}")
        print(f"   - 用户名: {walker.config['NAS_SERVER']['username']}")
        print(f"   - 输出格式: {walker.config['SCAN']['output_format']}")
        return True
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False


def test_config_creation():
    """测试默认配置文件创建"""
    print("\n🧪 测试默认配置文件创建...")
    
    test_config = "test_config.ini"
    
    try:
        # 删除测试配置文件（如果存在）
        if os.path.exists(test_config):
            os.remove(test_config)
            
        # 创建新的遍历器实例
        walker = NASWalker(test_config)
        
        if os.path.exists(test_config):
            print("✅ 默认配置文件创建成功")
            
            # 读取并显示配置内容
            with open(test_config, 'r', encoding='utf-8') as f:
                content = f.read()
                print("   配置文件内容:")
                for line in content.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        print(f"     {line}")
            
            # 清理测试文件
            os.remove(test_config)
            return True
        else:
            print("❌ 默认配置文件创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_output_formats():
    """测试输出格式功能"""
    print("\n🧪 测试输出格式功能...")
    
    try:
        walker = NASWalker()
        
        # 测试数据
        test_data = {
            "type": "directory",
            "name": "test",
            "path": "/test",
            "items": [
                {
                    "type": "file",
                    "name": "test.txt",
                    "path": "/test/test.txt",
                    "size": 1024,
                    "modified": "2024-01-01T00:00:00",
                    "permissions": "644"
                }
            ],
            "item_count": 1,
            "scan_time": "2024-01-01T00:00:00"
        }
        
        # 测试JSON格式
        json_file = "test_output.json"
        if walker.save_results(test_data, json_file):
            print("✅ JSON格式输出测试成功")
            os.remove(json_file)
        else:
            print("❌ JSON格式输出测试失败")
            return False
            
        # 测试TXT格式
        walker.config['SCAN']['output_format'] = 'txt'
        txt_file = "test_output.txt"
        if walker.save_results(test_data, txt_file):
            print("✅ TXT格式输出测试成功")
            os.remove(txt_file)
        else:
            print("❌ TXT格式输出测试失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 输出格式测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理功能"""
    print("\n🧪 测试错误处理功能...")
    
    try:
        # 测试无效配置文件
        invalid_config = "invalid_config.ini"
        with open(invalid_config, 'w') as f:
            f.write("[INVALID_SECTION]\nkey = value\n")
            
        try:
            walker = NASWalker(invalid_config)
            print("❌ 应该检测到无效配置")
            return False
        except ValueError:
            print("✅ 无效配置检测成功")
        finally:
            os.remove(invalid_config)
            
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始NAS目录遍历器测试...\n")
    
    tests = [
        ("配置文件加载", test_config_loading),
        ("默认配置创建", test_config_creation),
        ("输出格式功能", test_output_formats),
        ("错误处理功能", test_error_handling)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"⚠️  {test_name} 测试未通过")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！程序基本功能正常。")
        print("\n💡 下一步:")
        print("   1. 编辑 config.ini 文件，填入您的NAS服务器信息")
        print("   2. 运行 python nas_walker.py 开始扫描")
    else:
        print("⚠️  部分测试失败，请检查错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
