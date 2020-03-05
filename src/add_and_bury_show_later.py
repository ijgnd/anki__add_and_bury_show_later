import datetime
import os
import pickle
from pprint import pprint as pp
import time

import aqt
import aqt.addcards
from aqt.addcards import AddCards

from aqt.qt import *
from aqt.utils import (
    askUser,
    getOnlyText,
    getText,
    showInfo,
    tooltip)
from anki.lang import _
from anki.sound import clearAudioQueue
from anki.hooks import addHook, wrap

from .libs import inflect

from .config import gc

ii = inflect.engine()





"""
TODO
how to load icon in stylesheet?
- url(" data:image/png;base64,%s");  But https://bugreports.qt.io/browse/QTBUG-51081
- url("icons/right.svg");
- qrc:
"""

basic_stylesheet = """
QMenu::item {
    padding-top: 16px;
    padding-bottom: 16px;
    padding-right: 75px;
    padding-left: 20px;
    font-size: 15px;
}
QMenu::item:selected {
    background-color: #fd4332;
}

QCheckBox {
    padding-top: 16px;
    padding-bottom: 16px;
    padding-right: 75px;
    padding-left: 20px;
    font-size: 15px;
}


QSpinBox {
    font-size:18px;
    background-color: #eff0f1;
}

QSpinBox::down-button {
    subcontrol-origin: margin;
    subcontrol-position: center left;
    image: url("icons/right.svg");
    background-color: #ABABAB;
    border: 1px solid black;
    padding:0px;
    margin:0px;
    left: 1px;
    height: 24px;
    width: 50px;
}

QSpinBox::up-button {
    subcontrol-origin: margin;
    subcontrol-position: center right;
    image: url("icons/right.svg");
    background-color: #ABABAB;
    border: 1px solid black;
    padding:0px;
    margin:0px;
    right: 1px;
    height: 24px;
    width: 50px;
}
"""


addon_path = os.path.dirname(__file__)
user_files_folder = os.path.join(addon_path, "user_files")


def getfile():
    profileId = aqt.mw.pm.meta['id']
    picklefile = os.path.join(user_files_folder, "burylist__%d.pypickle" % profileId)
    return picklefile


def loaddict():
    pf = getfile()
    if os.path.isfile(pf):
        with open(pf, 'rb') as PO:
            try:
                burydict = pickle.load(PO)
            except:
                burydict = {}
    else:
        burydict = {}
    pp(burydict)


def savedict():
    pf = getfile()
    # pp(burydict)
    # prevent error after deleting add-on
    if os.path.exists(user_files_folder):
        with open(pf, 'wb') as PO:
            pickle.dump(burydict, PO)


def new_day_starts_at():
    # aqt/preferences.py
    if aqt.mw.col.schedVer() == 2:
        return aqt.mw.col.conf.get("rollover", 4) 
    else:
        # sched.py
        # self.today = int((time.time() - self.col.crt) // 86400)
        # # end of day cutoff
        # self.dayCutoff = self.col.crt + (self.today+1)*86400
        return datetime.datetime.fromtimestamp(aqt.mw.col.crt).hour


def now_adjusted_as_dtobj():
    return datetime.datetime.now() + datetime.timedelta(hours = new_day_starts_at())


def bury_today_and_clean():
    global burydict
    todayfmt = now_adjusted_as_dtobj().strftime("%Y-%m-%d")
    if todayfmt in burydict:
        aqt.mw.col.sched.buryCards(burydict[todayfmt])
        print('_____today buried, then deleted_______')
        pp(burydict[todayfmt])
        del burydict[todayfmt]
    for k in list(burydict):
        dat = datetime.datetime.strptime(k, "%Y-%m-%d")
        if dat < now_adjusted_as_dtobj():
            del burydict[k]


def addToBuryDict(cid, days):
    global burydict
    today = now_adjusted_as_dtobj()
    for d in range(days):
        then = today + datetime.timedelta(days=d)
        fmt = then.strftime("%Y-%m-%d")
        if fmt not in burydict:
            burydict[fmt] = []
        burydict[fmt].append(cid)
    savedict()
    pp('~~~~~~{}--------{}'.format(cid, days))
    pp(burydict)



addHook('profileLoaded', getfile)
addHook('profileLoaded', loaddict)
addHook('profileLoaded', bury_today_and_clean)
addHook('unloadProfile', savedict)


def addcounter(self):
    self.counter = 1
    self.must_reset_counter = False
    self.spread_days = gc("Siblings_spread_days")
AddCards.setupButtons = wrap(AddCards.setupButtons, addcounter)


def add_and_close(self):
    self.addCards()
    self.reject()
AddCards.add_and_close = add_and_close


def ask_to_reschedule(self):
    nd = getOnlyText("Reschedule with intervals of __ days: ")
    try:
        ndi = int(nd)
    except:
        tooltip('input is not an integer. Aborting')
    else:
        self.add_and_reschedule(ndi, ndi)
        if self.closeafter:
            self.reject()
AddCards.ask_to_reschedule = ask_to_reschedule


def ask_to_bury(self):
    nd = getOnlyText("Bury with intervals of __ days: ")
    try:
        ndi = int(nd)
    except:
        tooltip('input is not an integer. Aborting')
    else:
        self.add_and_bury(ndi, ndi)
        if self.closeafter:
            self.reject()
AddCards.ask_to_bury = ask_to_bury


def add_and_reschedule_with_counter(self, days):
    if self.must_reset_counter or (self.mw.app.keyboardModifiers() & Qt.AltModifier):
        self.counter = 0
        days = 1
    if self.must_reset_counter:
        self.must_reset_counter = False
    note = self.add_and_reschedule(days, days)
    if note:
        self.counter += 1
AddCards.add_and_reschedule_with_counter = add_and_reschedule_with_counter


def my_reset_KeepModel_compa(self):
    try:
        __import__("424778276").keepModelInAddCards
    except:
        self.onReset(keep=True)
    else:
        self.onResetSameModel(keep=True)
AddCards.my_reset_KeepModel_compa = my_reset_KeepModel_compa


def add_and_reschedule(self, mindays, maxdays, close=False):
    self.editor.saveAddModeVars()
    note = self.editor.note
    note = self.addNote(note)
    if not note:
        return

    # stop anything playing
    clearAudioQueue()
    self.my_reset_KeepModel_compa()
    self.mw.col.autosave()

    cards = note.cards()
    # if there is a deck override new cards can go to
    # different decks
    EaseForCards = gc("EaseForCards")
    if not (EaseForCards == "DeckSettings" or isinstance(EaseForCards, int)):
        showInfo("Error in Add-on config: illegal value in setting 'EaseForCards'. Aborting ... ")
        return
    if EaseForCards == "DeckSettings":
        perdeck = True
    for c in cards:
        if perdeck:
            conf = self.mw.col.decks.confForDid(c.did)
            factor = conf['new']['initialFactor']
        else:
            factor = EaseForCards * 10
        # maybe spread out cards. if siblings_spread_days is zero = disabled all siblings
        # will be scheduled for the same time frame.
        mindaysMod = mindays + c.ord * self.spread_days
        maxdaysMod = maxdays + c.ord * self.spread_days
        if mindaysMod >= 1:
            try:
                # running a non-existent hook doesn't throw an error
                __import__("323586997")
            except:
                self.mw.col.sched.reschedNewCards([c.id], factor, mindaysMod, maxdaysMod)
            else:
                # this uses the decks ease
                runHook("ReMemorize.rescheduleAll", [c.id], mindaysMod, maxdaysMod)
    if not gc("sibling_spread_days_remember_last", False):
        self.spread_days = gc("Siblings_spread_days")
    if self.closeafter or (self.mw.app.keyboardModifiers() & Qt.ShiftModifier):
        self.reject()
    return True
AddCards.add_and_reschedule = add_and_reschedule


def add_and_bury_with_counter(self, days):
    if self.must_reset_counter or (self.mw.app.keyboardModifiers() & Qt.AltModifier):
        self.counter = 0
        days = 1
    if self.must_reset_counter:
        self.must_reset_counter = False
    note = self.add_and_bury(days, days)
    if note:
        self.counter += 1
AddCards.add_and_bury_with_counter = add_and_bury_with_counter


def add_and_bury(self, mindays, maxdays, close=False):
    self.editor.saveAddModeVars()
    note = self.editor.note
    note = self.addNote(note)
    if not note:
        return

    # stop anything playing
    clearAudioQueue()
    self.my_reset_KeepModel_compa()
    self.mw.col.autosave()

    cards = note.cards()
    for c in cards:
        # maybe spread out cards. if siblings_spread_days is zero = disabled all siblings
        # will be scheduled for the same time frame.
        mindaysMod = mindays + c.ord * self.spread_days
        maxdaysMod = maxdays + c.ord * self.spread_days
        r = random.randint(mindaysMod, maxdaysMod)
        if r >= 1:
            addToBuryDict(c.id, r)
            self.mw.col.sched.buryCards([c.id])
    if not gc("sibling_spread_days_remember_last", False):
        self.spread_days = gc("Siblings_spread_days")
    if self.closeafter or (self.mw.app.keyboardModifiers() & Qt.ShiftModifier):
        self.reject()
    return True
AddCards.add_and_bury = add_and_bury


# mod of _addCards
def _add_as_nth_new(self, newindex):
    self.editor.saveAddModeVars()
    note = self.editor.note
    note = self.addNote(note)
    if not note:
        return
    tooltip(_("Added as first new"), period=500)
    # stop anything playing
    clearAudioQueue()
    self.my_reset_KeepModel_compa()
    self.mw.col.autosave()
    cids = [int(c.id) for c in note.cards()]
    # browser.py -  reposition
    # self.mw.checkpoint(_("Reposition"))
    aqt.mw.col.sched.sortCards(
        cids, start=newindex, step=1,
        shuffle=False, shift=True)
    aqt.mw.requireReset()
AddCards._add_as_nth_new = _add_as_nth_new






def _addCardsMod(self):
    self.editor.saveAddModeVars()
    note = self.editor.note
    note = self.addNote(note)
    if not note:
        return
    tooltip(_("Added"), period=500)
    # stop anything playing
    clearAudioQueue()
    self.my_reset_KeepModel_compa()
    self.mw.col.autosave()
    if self.closeafter or (self.mw.app.keyboardModifiers() & Qt.ShiftModifier):
        self.reject()
AddCards._addCardsMod = _addCardsMod


def resetcounter(self):
    # ugly workaround with self.must_reset_counter because just setting self.counter = 1
    # in this function for some reason didn't work and I didn't want to investigate since
    # I could just reuse the solution from closeaftertoggle. This was much quicker than one
    # thinking about it.
    self.must_reset_counter^=True
AddCards.resetcounter = resetcounter


def closeaftertoggle(self):
    self.closeafter^=True
AddCards.closeaftertoggle = closeaftertoggle


def my_make_submenu(self, submenu, dict_, func):
    for l in dict_:
        if l[0] == "":
            submenu.addSeparator()
        else:
            a = submenu.addAction(l[0])
            if l[3]:
                a.setShortcut(QKeySequence(l[3]))   # just to add it to the gui
            a.triggered.connect(lambda _, s=self, lower=l[1], upper=l[2]: func(lower, upper))
            a = QShortcut(QKeySequence(l[3]), self)
            a.activated.connect(lambda s=self, lower=l[1], upper=l[2]: func(lower, upper))


def setspread(self, val):
    self.spread_days = val
AddCards.setspread = setspread


def regular_add_and_close(self):
    self.closeafter = True
    self._addCardsMod()
AddCards.regular_add_and_close = regular_add_and_close


def myadd(self):
    outerm = QMenu(self.editor.widget)
    outerm.setStyleSheet(basic_stylesheet)
    self.closeafter = False

    if not gc("Modify add and ctrl+enter"):  # nevertheless add regular on top to quickly close
        regul = outerm.addAction("regular add (and close)")
        regul.triggered.connect(self.regular_add_and_close)

    cb_close = QCheckBox("close afterwards?")
    cb_close.toggled.connect(self.closeaftertoggle)
    a = QWidgetAction(self.editor.widget)
    a.setDefaultWidget(cb_close)
    outerm.addAction(a)

    cb_reset = QCheckBox("reset counter?")
    cb_reset.toggled.connect(self.resetcounter)
    a = QWidgetAction(self.editor.widget)
    a.setDefaultWidget(cb_reset)
    outerm.addAction(a)

    sb = QSpinBox(outerm)
    sb.setMinimum(0)
    sb.setValue(gc("Siblings_spread_days"))
    sb.valueChanged.connect(lambda v=sb.value(): self.setspread(v))
    a = QWidgetAction(self.editor.widget)
    a.setDefaultWidget(sb)
    outerm.addAction(a)

    if gc("new_positions_absolute"):
        npaMen = outerm.addMenu('add as nth (non-suspended) new card:')
        # notes with new unsuspended cards
        nwnuc = aqt.mw.col.db.list(
            """select id from cards where type = 0 and queue != -1 and ord = 0 order by due asc""")
            # all card templates (ord) have teh samed due number
        latest = False
        for i in gc("new_positions_absolute"):
            index = max(i-1, 0)
            if index <= len(nwnuc):
                fin = npaMen.addAction("{}".format(ii.ordinal(index + 1)))
                fin.triggered.connect(lambda _, i=index: self._add_as_nth_new(i))
            elif not latest:
                latest = True
                fin = npaMen.addAction("{}".format(ii.ordinal(len(nwnuc) + 1)))
                if len(nwnuc) > 0:
                    try: 
                        highest_due = aqt.mw.col.getCard(nwnuc[-1]).due
                    except:
                        pass
                    else:
                        fin.triggered.connect(lambda _, i=highest_due+1: self._add_as_nth_new(i)) 
    else:
        fin = outerm.addAction("add as first due new card")
        fin.triggered.connect(lambda _, i=0: self._add_as_nth_new(i))
    outerm.addSeparator()

    bac = outerm.addAction("add+bury - %d days, counter+1" % self.counter)
    bac.triggered.connect(lambda _, c=self.counter: self.add_and_bury_with_counter(c))

    buMen = outerm.addMenu('add+bury')
    if gc("bury_days"):
        my_make_submenu(self, buMen, gc("bury_days"), self.add_and_bury)

    sask = outerm.addAction("add+bury - ask")
    sask.triggered.connect(self.ask_to_bury)

    if gc("Reschedule_show", True):
        outerm.addSeparator()
        rac = outerm.addAction("add+reschedule - %d days, counter+1" % self.counter)
        rac.triggered.connect(lambda _, c=self.counter: self.add_and_reschedule_with_counter(c))
        rarsd = outerm.addMenu('add+reschedule')
        rask = outerm.addAction("add+reschedule - ask")
        rask.triggered.connect(self.ask_to_reschedule)
        resch_days = gc("reschedule_days", False)
        if resch_days:
            my_make_submenu(self, rarsd, resch_days, self.add_and_reschedule)

    if gc("Modify add and ctrl+enter", True):
        defaultadd = outerm.addAction("add (default)")
        defaultadd.triggered.connect(self._addCardsMod)
        outerm.setActiveAction(defaultadd)
    outerm.exec_(QCursor.pos())



if gc("Modify add and ctrl+enter", True):
    # AddCards._addCards = wrap(AddCards._addCards, myadd, "around")
    AddCards._addCards = myadd
else:
    AddCards.myadd = myadd
    def right_helper(self):
        self.editor.saveNow(self.myadd)
    AddCards.right_helper = right_helper
    def menu_as_right_click(self):
        self.addButton.setContextMenuPolicy(Qt.CustomContextMenu)
        self.addButton.customContextMenuRequested.connect(self.right_helper)
    AddCards.setupButtons = wrap(AddCards.setupButtons, menu_as_right_click)

