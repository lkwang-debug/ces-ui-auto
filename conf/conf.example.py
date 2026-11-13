# Copy to conf.py and fill actual environment values.
import os
from selenium.webdriver.common.by import By
'\n配置文件总是项目中必不可少的部分！\n将固定不变的信息集中在固定的文件中\n这个conf文件我模仿了Django的settings.py文件的设置风格，但是又有些许差异\n'

class ConfigManager(object):
    """
    在这个文件中我们可以设置自己的各个目录，也可以查看自己当前的目录。

    遵循了约定：不变的常量名全部大写，函数名小写。看起来整体美观。
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ELEMENT_PATH = os.path.join(BASE_DIR, 'page_element')
    REPORT_FILE = os.path.join(BASE_DIR, 'report.html')
    LOCATE_MODE = {'css': By.CSS_SELECTOR, 'xpath': By.XPATH, 'name': By.NAME, 'id': By.ID, 'class': By.CLASS_NAME}
    EMAIL_INFO = {'username': '', 'password': '', 'smtp_host': '', 'smtp_port': 465}
    ADDRESSEE = []
    BAIDU_URL = 'https://www.baidu.com'
    FILE_UPLOAD = 'https://letcode.in/file'
    WHOLE_PATH = './screenshots/简单验证码.png'
    CROP_PATH = './screenshots/crop_pic.png'
    HST_URL = os.getenv('UIAUTO_BASE_URL', 'http://127.0.0.1:28080')
    USERNAME = os.getenv('UIAUTO_USERNAME', 'admin')
    PASSWORD = os.getenv('UIAUTO_PASSWORD', '')
    LOGIN_TEST_USERNAME = os.getenv('UIAUTO_LOGIN_TEST_USERNAME', '')
    LOGIN_TEST_PASSWORD = os.getenv('UIAUTO_LOGIN_TEST_PASSWORD', '')
    PROFILE_PASSWORD_USERNAME = os.getenv('UIAUTO_PROFILE_PASSWORD_USERNAME', '')
    PROFILE_PASSWORD_PASSWORD = os.getenv('UIAUTO_PROFILE_PASSWORD_PASSWORD', '')
    RESTRICTED_USERNAME = os.getenv('UIAUTO_RESTRICTED_USERNAME', '')
    RESTRICTED_PASSWORD = os.getenv('UIAUTO_RESTRICTED_PASSWORD', '')
    CHROMEDRIVER_PATH = os.getenv('UIAUTO_CHROMEDRIVER_PATH', os.path.join(BASE_DIR, '.venv-local', 'Scripts', 'chromedriver.exe'))
    OCR_MAX_ATTEMPTS = int(os.getenv('UIAUTO_OCR_MAX_ATTEMPTS', '5'))
    SECURITY_VERIFY_MODE = os.getenv('UIAUTO_SECURITY_VERIFY_MODE', 'auto').strip().lower()
    SECURITY_VERIFY_MAX_ATTEMPTS = int(os.getenv('UIAUTO_SECURITY_VERIFY_MAX_ATTEMPTS', '5'))
    SECURITY_VERIFY_WAIT_SECONDS = float(os.getenv('UIAUTO_SECURITY_VERIFY_WAIT_SECONDS', '12'))
    SECURITY_VERIFY_MIN_SCORE = float(os.getenv('UIAUTO_SECURITY_VERIFY_MIN_SCORE', '0.15'))
    SECURITY_VERIFY_MIN_MARGIN = float(os.getenv('UIAUTO_SECURITY_VERIFY_MIN_MARGIN', '0.03'))
    MENU_VISUAL_DWELL_SECONDS = float(os.getenv('UIAUTO_MENU_VISUAL_DWELL_SECONDS', '2'))
    FULL_PERFORMANCE_BUDGET_SECONDS = int(os.getenv('UIAUTO_FULL_PERFORMANCE_BUDGET_SECONDS', '1080'))
    DOWNLOAD_DIR = os.getenv('UIAUTO_DOWNLOAD_DIR', os.path.join(BASE_DIR, '.runtime', 'downloads'))
    IMPORT_TEMPLATE_DIR = os.getenv('UIAUTO_IMPORT_TEMPLATE_DIR', os.path.join(BASE_DIR, '.runtime', 'imports'))
    IMPORT_ORGANIZATION_PATH = os.getenv('UIAUTO_IMPORT_ORGANIZATION_PATH', '测试组织')
    RECORD_TASK_KEYWORD = ''
    MEETING_RECORD_ROOM_ID = os.getenv('UIAUTO_MEETING_RECORD_ROOM_ID', '')
    MEETING_RECORD_START_TIME = os.getenv('UIAUTO_MEETING_RECORD_START_TIME', '')
    TERMINAL_LOG_USERNAME = os.getenv('UIAUTO_TERMINAL_LOG_USERNAME', '')
    TERMINAL_LOG_DEVICE_ID = os.getenv('UIAUTO_TERMINAL_LOG_DEVICE_ID', '')
    TERMINAL_LOG_TYPE = os.getenv('UIAUTO_TERMINAL_LOG_TYPE', '终端日志')
    TERMINAL_LOG_TRIGGER_COMMAND = os.getenv('UIAUTO_TERMINAL_LOG_TRIGGER_COMMAND', '')
    UNDEPLOYED_SERVER_LOG_TABS = tuple((tab.strip() for tab in os.getenv('UIAUTO_UNDEPLOYED_SERVER_LOG_TABS', '节点服务器' if HST_URL.rstrip('/') == 'https://127.0.0.1:28443' else '').split(',') if tab.strip()))
    ACCEPTANCE_MODE = os.getenv('UIAUTO_ACCEPTANCE_MODE', '1').strip().lower() in {'1', 'true', 'yes', 'on'}
    PRODUCT_PROFILE = os.getenv('UIAUTO_PRODUCT_PROFILE', 'auto')
    HTTPS_VERIFY_CERTIFICATE = os.getenv('UIAUTO_HTTPS_VERIFY_CERTIFICATE', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
    REQUIRED_CAPABILITIES = {value.strip() for value in os.getenv('UIAUTO_REQUIRED_CAPABILITIES', '').split(',') if value.strip()}
    EXCLUDED_CAPABILITIES = {}
    AI_CR_API_KEY = os.getenv('UIAUTO_AI_CR_API_KEY', '')
    AI_OPENAI_API_KEY = os.getenv('UIAUTO_AI_OPENAI_API_KEY', '')
    AI_CONNECT_SUCCESS_TIMEOUT = int(os.getenv('UIAUTO_AI_SUCCESS_TIMEOUT', '10'))
    AI_CONNECT_FAILURE_TIMEOUT = int(os.getenv('UIAUTO_AI_FAILURE_TIMEOUT', '60'))
    AI_MODEL_CONFIGS = ({'key': 'deepseek', 'name': 'Deepseek', 'vendor': 'Deepseek', 'model': 'deepseek-v4-flash', 'url': 'http://127.0.0.1:3000/api/v1/chat/completions', 'api_key': AI_CR_API_KEY}, {'key': 'openai_internal', 'name': 'OpenAiInternalGpt61Sol', 'vendor': 'OpenAI兼容协议', 'model': 'gpt-6.1-sol', 'url': 'http://127.0.0.1:8080/v1/chat/completions', 'api_key': AI_OPENAI_API_KEY}, {'key': 'glm', 'name': 'glm-5.3', 'vendor': '智谱', 'model': 'glm-5.3', 'url': 'http://127.0.0.1:3000/api/v1/chat/completions', 'api_key': AI_CR_API_KEY})
    FACE_IMAGE_DIR = os.getenv('UIAUTO_FACE_IMAGE_DIR', os.path.join(BASE_DIR, 'data', 'image'))
