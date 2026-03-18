# ==========================================
# 💾 记忆与上下文管理模块 (预留 Hook)
# ==========================================
class MemoryManager:
    """处理长文本和 Base64 图片的上下文溢出问题"""
    
    @staticmethod
    def append_and_prune(messages: list, new_msg: dict, max_images: int = 1):
        """
        核心逻辑：将新消息加入列表，并清理历史消息中多余的图片。
        大模型不需要看之前的废弃截图，只需要看最新的一张。
        """
        messages.append(new_msg)
        
        # 预留的图片清理逻辑：
        # 倒序遍历 messages，如果发现 type == 'image_url' 的内容，
        # 保留最近的 max_images 张，把更早的图片替换为文本 "[历史图片已清理以释放内存]"
        image_count = 0
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg.get("content"), list):
                for part in msg["content"]:
                    if part.get("type") == "image_url":
                        image_count += 1
                        if image_count > max_images:
                            # 替换掉庞大的 Base64 字符串
                            part["type"] = "text"
                            part["text"] = "[历史场景截图已释放]"
                            part.pop("image_url", None)
        return messages