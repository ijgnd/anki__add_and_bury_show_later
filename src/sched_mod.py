from anki.utils import intTime
import random
from anki.sched import Scheduler
from anki.schedv2 import Scheduler as schedV2


# slight modification of reschedCards from anki/sched.py which is
#    Copyright: Damien Elmes <anki@ichi2.net>
#    License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# I inserted the function parameter "factor",removed remFromDyn,added the tooltip
def reschedNewCards(self, ids, factor, imin, imax):
    "Put cards in review queue with a new interval in days (min, max)."
    d = []
    t = self.today
    mod = intTime()
    for id in ids:
        r = random.randint(imin, imax)
        d.append(dict(id=id, due=r+t, ivl=max(1, r), mod=mod,
                        usn=self.col.usn(), fact=int(factor)))
    # self.remFromDyn(ids)   #Cards just created can't be in a filtered deck
    self.col.db.executemany("""
update cards set type=2,queue=2,ivl=:ivl,due=:due,odue=0,
usn=:usn,mod=:mod,factor=:fact where id=:id""",
                            d)
    self.col.log(ids)

    if len(ids) == 1:
        tooltip(_("Added and rescheduled for %d" % d[0]['ivl']), period=800)
    else:
        ivls = []
        for c in d:
            ivls.append(c['ivl'])
        print(ivls)
        mmsg = "Added and rescheduled cards with intervals between {} and {}".format(
               min(ivls), max(ivls))
        tooltip(mmsg, period=800)
Scheduler.reschedNewCards = reschedNewCards
schedV2.reschedNewCards = reschedNewCards 
