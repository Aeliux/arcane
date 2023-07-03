# ba_meta require api 8

import babase as ba
import baplus


original_get_purchased = baplus.PlusSubsystem.get_purchased

@staticmethod
def get_purchased(item):
    if item.startswith('characters.') or item.startswith('icons.'):
        return original_get_purchased(item)
    return True


# ba_meta export plugin
class Unlock(ba.Plugin):
    def on_app_running(self):
        ba.app.classic.accounts.have_pro = lambda: True
        baplus.PlusSubsystem.get_purchased = get_purchased
