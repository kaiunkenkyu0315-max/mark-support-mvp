"""会社・PMS基本情報を含めた初期設定全体の進捗判定。

従来の intake 側 SetupStatus は STEP1 以降の状態を判定する。
STEP0（会社・PMS基本情報）を正式な初期設定工程として加えたため、
会社情報が保存済みなら、STEP1未回答でも「未着手」ではなく「設定中」とする。
"""

from app import company_profile, intake_demo_state
from app.intake_demo_state import IntakeDemoState
from app.intake_schemas import SetupStatus


def get_effective_setup_status(state: IntakeDemoState) -> SetupStatus:
    """STEP0を含めた利用者向けの初期設定状態を返す。"""

    intake_status = intake_demo_state.get_setup_status(state)
    if (
        intake_status == SetupStatus.NOT_STARTED
        and company_profile.get_state().configured
    ):
        return SetupStatus.IN_PROGRESS
    return intake_status
