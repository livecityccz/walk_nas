#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAS目录遍历工具
支持SSH协议，递归遍历NAS服务器上的目录结构
"""

import os
import json
import configparser
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import paramiko
import stat


class NASWalker:
    """NAS目录遍历器"""
    
    def __init__(self, config_file: str = "config.ini"):
        """
        初始化NAS遍历器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = None
        self.ssh_client = None
        self.sftp_client = None
        self.setup_logging()
        self.load_config()
        
    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('nas_walker.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_file):
                self.create_default_config()
                
            self.config = configparser.ConfigParser()
            self.config.read(self.config_file, encoding='utf-8')
            
            # 验证必要的配置项
            required_sections = ['NAS_SERVER', 'CONNECTION', 'SCAN']
            for section in required_sections:
                if section not in self.config:
                    raise ValueError(f"配置文件缺少必要的 [{section}] 部分")
                    
            self.logger.info("配置文件加载成功")
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
            
    def create_default_config(self):
        """创建默认配置文件"""
        config = configparser.ConfigParser()
        
        config['NAS_SERVER'] = {
            'ip': '192.168.1.100',
            'username': 'your_username',
            'password': 'your_password'
        }
        
        config['CONNECTION'] = {
            'protocol': 'ssh',
            'port': '22',
            'timeout': '30'
        }
        
        config['SCAN'] = {
            'root_path': '/home',
            'max_depth': '10',
            'include_hidden': 'false',
            'output_format': 'json',
            'output_file': 'nas_structure.json'
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)
            
        self.logger.info(f"已创建默认配置文件: {self.config_file}")
        
    def connect_to_nas(self) -> bool:
        """
        连接到NAS服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 获取连接参数
            ip = self.config['NAS_SERVER']['ip']
            username = self.config['NAS_SERVER']['username']
            password = self.config['NAS_SERVER']['password']
            port = int(self.config['CONNECTION']['port'])
            timeout = int(self.config['CONNECTION']['timeout'])
            
            # 创建SSH客户端
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 尝试连接
            self.ssh_client.connect(
                hostname=ip,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # 创建SFTP客户端
            self.sftp_client = self.ssh_client.open_sftp()
            
            self.logger.info(f"成功连接到NAS服务器: {ip}:{port}")
            return True
                
        except Exception as e:
            self.logger.error(f"连接NAS服务器失败: {e}")
            return False
            
    def scan_directory(self, remote_path: str, max_depth: int = 10, current_depth: int = 0) -> Dict[str, Any]:
        """
        递归扫描目录结构
        
        Args:
            remote_path: 远程目录路径
            max_depth: 最大扫描深度
            current_depth: 当前扫描深度
            
        Returns:
            Dict: 目录结构信息
        """
        if current_depth > max_depth:
            return {"type": "directory", "name": os.path.basename(remote_path), "truncated": True}
            
        try:
            # 获取目录内容
            items = self.sftp_client.listdir_attr(remote_path)
            
            result = {
                "type": "directory",
                "name": os.path.basename(remote_path) or "/",
                "path": remote_path,
                "items": [],
                "item_count": 0,
                "scan_time": datetime.now().isoformat()
            }
            
            # 扫描子项
            for item in items:
                if item.filename in ['.', '..']:
                    continue
                    
                item_path = os.path.join(remote_path, item.filename)
                
                try:
                    # 检查是否为目录
                    if stat.S_ISDIR(item.st_mode):
                        if current_depth < max_depth:
                            sub_result = self.scan_directory(item_path, max_depth, current_depth + 1)
                            result["items"].append(sub_result)
                        else:
                            result["items"].append({
                                "type": "directory",
                                "name": item.filename,
                                "path": item_path,
                                "truncated": True
                            })
                    else:
                        # 获取文件信息
                        file_info = {
                            "type": "file",
                            "name": item.filename,
                            "path": item_path,
                            "size": item.st_size,
                            "modified": datetime.fromtimestamp(item.st_mtime).isoformat(),
                            "permissions": oct(item.st_mode)[-3:],
                            "owner": item.st_uid,
                            "group": item.st_gid
                        }
                        result["items"].append(file_info)
                        
                except PermissionError:
                    # 权限不足
                    result["items"].append({
                        "type": "error",
                        "name": item.filename,
                        "path": item_path,
                        "error": "权限不足"
                    })
                except Exception as e:
                    # 其他错误
                    result["items"].append({
                        "type": "error",
                        "name": item.filename,
                        "path": item_path,
                        "error": str(e)
                    })
                    
            result["item_count"] = len(result["items"])
            return result
            
        except PermissionError:
            return {
                "type": "error",
                "name": os.path.basename(remote_path),
                "path": remote_path,
                "error": "权限不足"
            }
        except Exception as e:
            return {
                "type": "error",
                "name": os.path.basename(remote_path),
                "path": remote_path,
                "error": str(e)
            }
            
    def get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        try:
            # 获取系统信息
            stdin, stdout, stderr = self.ssh_client.exec_command('uname -a')
            system_info = stdout.read().decode().strip()
            
            # 获取磁盘使用情况
            stdin, stdout, stderr = self.ssh_client.exec_command('df -h')
            disk_info = stdout.read().decode().strip()
            
            return {
                "system": system_info,
                "disk_usage": disk_info
            }
        except Exception as e:
            self.logger.warning(f"无法获取系统信息: {e}")
            return {}
            
    def save_results(self, data: Dict[str, Any], output_file: str = None) -> bool:
        """
        保存扫描结果到文件
        
        Args:
            data: 扫描结果数据
            output_file: 输出文件名
            
        Returns:
            bool: 保存是否成功
        """
        try:
            if output_file is None:
                output_file = self.config['SCAN']['output_file']
                
            output_format = self.config['SCAN']['output_format'].lower()
            
            if output_format == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif output_format == 'txt':
                with open(output_file, 'w', encoding='utf-8') as f:
                    self._write_text_format(data, f)
            elif output_format == 'md':
                with open(output_file, 'w', encoding='utf-8') as f:
                    self._write_markdown_format(data, f)
            else:
                raise ValueError(f"不支持的输出格式: {output_format}")
                
            self.logger.info(f"结果已保存到: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")
            return False
            
    def _write_text_format(self, data: Dict[str, Any], file_handle, indent: int = 0):
        """将数据写入文本格式"""
        prefix = "  " * indent
        
        if data["type"] == "directory":
            file_handle.write(f"{prefix}[DIR] {data['name']}\n")
            if "items" in data and data["items"]:
                for item in data["items"]:
                    self._write_text_format(item, file_handle, indent + 1)
        elif data["type"] == "file":
            size_mb = data.get("size", 0) / (1024 * 1024)
            file_handle.write(f"{prefix}[FILE] {data['name']} ({size_mb:.2f} MB)\n")
        elif data["type"] == "error":
            file_handle.write(f"{prefix}[ERROR] {data['name']} - {data.get('error', '未知错误')}\n")
            
    def _write_markdown_format(self, data: Dict[str, Any], file_handle, indent: int = 0):
        """将数据写入Markdown格式"""
        if indent == 0:
            # 写入文档标题和系统信息
            file_handle.write(f"# NAS目录结构报告\n\n")
            file_handle.write(f"**扫描时间**: {data.get('scan_time', '未知')}\n\n")
            
            if "system_info" in data:
                sys_info = data["system_info"]
                file_handle.write("## 系统信息\n\n")
                file_handle.write(f"**操作系统**: {sys_info.get('system', '未知')}\n\n")
                file_handle.write("### 磁盘使用情况\n\n")
                file_handle.write("```\n")
                file_handle.write(sys_info.get('disk_usage', '未知'))
                file_handle.write("\n```\n\n")
            
            file_handle.write("## 目录结构\n\n")
        
        # 根据类型写入不同的Markdown格式
        if data["type"] == "directory":
            # 目录使用标题格式
            heading_level = min(indent + 2, 6)  # 限制标题级别为2-6
            heading_marker = "#" * heading_level
            file_handle.write(f"{heading_marker} 📁 {data['name']}\n\n")
            
            if "items" in data and data["items"]:
                # 创建目录内容表格
                file_handle.write("| 类型 | 名称 | 大小 | 修改时间 | 权限 |\n")
                file_handle.write("|------|------|------|----------|------|\n")
                
                for item in data["items"]:
                    if item["type"] == "file":
                        size_mb = item.get("size", 0) / (1024 * 1024)
                        size_str = f"{size_mb:.2f} MB" if size_mb > 0 else "0 B"
                        file_handle.write(f"| 📄 文件 | {item['name']} | {size_str} | {item.get('modified', '未知')} | {item.get('permissions', '000')} |\n")
                    elif item["type"] == "directory":
                        file_handle.write(f"| 📁 目录 | {item['name']} | - | - | - |\n")
                    elif item["type"] == "error":
                        file_handle.write(f"| ❌ 错误 | {item['name']} | - | - | {item.get('error', '未知错误')} |\n")
                
                file_handle.write("\n")
                
                # 递归处理子目录
                for item in data["items"]:
                    if item["type"] == "directory" and "items" in item:
                        self._write_markdown_format(item, file_handle, indent + 1)
                        
        elif data["type"] == "file":
            # 文件信息
            size_mb = data.get("size", 0) / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB" if size_mb > 0 else "0 B"
            file_handle.write(f"- **📄 {data['name']}** ({size_str})\n")
            file_handle.write(f"  - 路径: `{data['path']}`\n")
            file_handle.write(f"  - 修改时间: {data.get('modified', '未知')}\n")
            file_handle.write(f"  - 权限: {data.get('permissions', '000')}\n")
            file_handle.write(f"  - 所有者: {data.get('owner', '未知')}\n")
            file_handle.write(f"  - 组: {data.get('group', '未知')}\n\n")
            
        elif data["type"] == "error":
            # 错误信息
            file_handle.write(f"- **❌ {data['name']}**\n")
            file_handle.write(f"  - 路径: `{data['path']}`\n")
            file_handle.write(f"  - 错误: {data.get('error', '未知错误')}\n\n")
            
    def run_scan(self) -> bool:
        """
        执行完整的扫描流程
        
        Returns:
            bool: 扫描是否成功
        """
        try:
            self.logger.info("开始NAS目录扫描...")
            
            # 连接NAS
            if not self.connect_to_nas():
                return False
                
            # 获取扫描参数
            root_path = self.config['SCAN']['root_path']
            max_depth = int(self.config['SCAN']['max_depth'])
            
            # 执行扫描
            self.logger.info(f"开始扫描目录: {root_path}, 最大深度: {max_depth}")
            
            # 获取系统信息
            system_info = self.get_system_info()
            if system_info:
                self.logger.info(f"系统信息: {system_info.get('system', '未知')}")
            
            result = self.scan_directory(root_path, max_depth)
            
            # 添加系统信息到结果中
            if system_info:
                result["system_info"] = system_info
            
            # 保存结果
            if self.save_results(result):
                self.logger.info("扫描完成")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"扫描过程中发生错误: {e}")
            return False
        finally:
            # 清理连接
            if self.sftp_client:
                try:
                    self.sftp_client.close()
                except:
                    pass
            if self.ssh_client:
                try:
                    self.ssh_client.close()
                except:
                    pass


def main():
    """主函数"""
    try:
        # 创建NAS遍历器实例
        walker = NASWalker()
        
        # 执行扫描
        if walker.run_scan():
            print("✅ NAS目录扫描完成！")
            print(f"📁 结果已保存到: {walker.config['SCAN']['output_file']}")
        else:
            print("❌ NAS目录扫描失败！")
            print("请检查配置文件、网络连接和权限设置")
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        print("请检查错误日志文件: nas_walker.log")


if __name__ == "__main__":
    main()
