import time
from winotify import Notification, audio
from winotify.audio import LoopingAlarm2

notification = Notification(
    app_id="ROGUN",
    title="""로건이의 행동 변화가 감지되었습니다.""",
    msg="LYING → WALK",
    icon=r'G:\zer0ken\rogun-app\resources\icon.ico'
)
notification.set_audio(sound=LoopingAlarm2, loop=False)
# 버튼 추가 (URL로 이동)
notification.add_actions(label="로건이 보러 가기", launch="http://localhost:8501/")
# 알림 보내기
time.sleep(5)
notification.show()                                                          