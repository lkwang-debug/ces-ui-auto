"""One serial run per target/account across project copies on Windows."""
import ctypes
import hashlib
import os
from ctypes import wintypes


class RunLock:
    def __init__(self, target, username):
        self.key = hashlib.sha256((target.rstrip('/')+'|'+username).encode()).hexdigest()[:24]
        self.handle = None

    def __enter__(self):
        if os.name != 'nt':
            raise RuntimeError('本项目串行运行锁当前仅支持 Windows')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        self.handle = kernel.CreateMutexW(None, False, 'Local\\CES_UI_'+self.key)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), '无法创建运行锁')
        if kernel.WaitForSingleObject(self.handle, 0) not in (0,128):
            kernel.CloseHandle(self.handle)
            self.handle = None
            raise RuntimeError('同一环境与账号已有自动化运行，未启动第二轮；请等待现有运行结束。')
        return self

    def __exit__(self, *exc):
        if self.handle:
            self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
