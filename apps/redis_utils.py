import threading

class MemoryStorageUtil:
    _storage = {}
    _lock = threading.Lock()

    #def __init__(self, host='', port=, password=''):
    #    pass

    def set_value(self, redis_key, redis_data, ex=None):
        try:
            print(f'{redis_key}{redis_data}{ex}')
            with self._lock:
                self._storage[redis_key] = redis_data
            return True
        except Exception as e:
            print(f"设置值失败: {e}")
            return False
    
    def rpush_value(self, redis_key, qa_task_scheduler, pre_sales_scheduler, global_step):
        try:
            with self._lock:
                self._storage["%s_qa_task_scheduler"%(redis_key)] = qa_task_scheduler
                self._storage["%s_pre_sales_scheduler"%(redis_key)] = pre_sales_scheduler
                self._storage["%s_global_step"%(redis_key)] = global_step
            return True
        except Exception as e:
            print(f"设置值失败: {e}")
            return False
    
    def rpull_value(self, redis_key):
        try:
            with self._lock:
                qa_task_scheduler = self._storage.get("%s_qa_task_scheduler"%(redis_key))
                pre_sales_scheduler = self._storage.get("%s_pre_sales_scheduler"%(redis_key))
                global_step = self._storage.get("%s_global_step"%(redis_key))
            return qa_task_scheduler, pre_sales_scheduler, global_step
        except Exception as e:
            print(f"获取值失败: {e}")
            return None, None, None
    
    def get_value(self, key):
        try:
            with self._lock:
                value = self._storage.get(key)
                if value is None:
                    print(f"DEBUG: get_value - key '{key}' 不存在于存储中")
                return value
        except Exception as e:
            print(f"获取值失败: {e}")
            print(f"ERROR: get_value 异常, key: {key}, error: {e}")
            return None

    def delete_key(self, key):
        try:
            with self._lock:
                if key in self._storage:
                    del self._storage[key]
                    return 1
                return 0
        except Exception as e:
            print(f"删除键失败: {e}")
            return 0

    def exists_key(self, key):
        try:
            with self._lock:
                return key in self._storage
        except Exception as e:
            print(f"检查键存在失败: {e}")
            return False

    def list_session_keys(self):
        try:
            with self._lock:
                return [
                    k for k in self._storage.keys()
                    if not k.endswith("_qa_task_scheduler")
                    and not k.endswith("_pre_sales_scheduler")
                    and not k.endswith("_global_step")
                ]
        except Exception as e:
            print(f"列出会话键失败: {e}")
            return []

    def increment_key(self, key, amount=1):
        try:
            with self._lock:
                current_value = self._storage.get(key, "0")
                try:
                    new_value = int(current_value) + amount
                except (ValueError, TypeError):
                    new_value = amount
                self._storage[key] = str(new_value)
                return new_value
        except Exception as e:
            print(f"增加键值失败: {e}")
            return None
    def expire_key(self, key, time):
        try:
            return True
        except Exception as e:
            print(e)
            return False
    @staticmethod
    def close_pool():
        pass

if __name__ == "__main__":
    redis_util = MemoryStorageUtil(host='', port=0000)
    redis_util.set_value("test_key", "eee", ex=100)
    print(redis_util.get_value("test_key"))
    print(redis_util.exists_key("test_key"))
    MemoryStorageUtil.close_pool()
