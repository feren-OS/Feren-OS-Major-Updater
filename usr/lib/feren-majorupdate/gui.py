#!/usr/bin/python3

import os
import gi
import subprocess
import sys
import threading
import getpass
import time

if len(sys.argv) == 1 or len(sys.argv) > 4:
    print("Invalid number of arguments")
    exit()

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, Gdk, GdkPixbuf

import apt
cache = apt.Cache()

class init():
    stepsdone = ""
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file('/usr/lib/feren-majorupdate/gui.glade')
        self.win = self.builder.get_object('mainwind')
        self.win.connect('delete-event', Gtk.main_quit)
        
        self.pagestack = self.builder.get_object('stack1')
        
        #PangoFont = Pango.FontDescription("Tahoma 12")
        #self.win.modify_font(PangoFont)
        
        self.win.set_icon_name('system-upgrade')
        
        self.backbtn = self.builder.get_object('backbtn')
        self.backbtn.connect('clicked', self.back_click)
        self.nextbtn = self.builder.get_object('nextbtn')
        self.nextbtn.connect('clicked', self.next_click)
        self.cancelbtn = self.builder.get_object('cancelbtn')
        self.cancelbtn.connect('clicked', self.cancel_click)
        self.updatebtn = self.builder.get_object('doupdootbtn')
        self.updatebtn.connect('clicked', self.update_click)
        
        self.syscodename = sys.argv[1]
        try:
            self.sysarch = sys.argv[2]
        except:
            self.sysarch = ""
        try:
            self.systype = sys.argv[3]
        except:
            self.systype = "standard"
        
        if self.syscodename not in ['xenial', 'bionic', 'focal']:
            print("This codename isn't supported.")
            Gtk.main_quit()
        
        if self.sysarch == "i686":
            self.pagestack.set_visible_child(self.builder.get_object('pagei386'))
        else:
            #Page 1
            self.builder.get_object('opentimeshiftbtn').connect('clicked', self.timeshift_1_click)
            
            #Page 2
            self.gotoferenbtn = self.builder.get_object('btnclassictransition')
            self.gotoferenbtn.connect('clicked', self.transition_confirm_click)
            self.gotomintbtn = self.builder.get_object('btnclassicmint')
            self.gotomintbtn.connect('clicked', self.gotomint_confirm_click)
            self.allowmintupgrade = self.builder.get_object('mintenabled')
            self.allowferentransition = self.builder.get_object('ferencinn2plasenabled')
            
            #Page 5
            self.grstate = self.builder.get_object('gettingreadystatus')
            self.grprogress = self.builder.get_object('gettingreadyprogress')
            
            #Page 7
            self.restarttimeleft = self.builder.get_object('restarttimeleft')
            self.builder.get_object('restartnowbtn').connect('clicked', self.restart_now)
            
            self.mintinstead = False
            self.ferentransitioninstead = False
            
            self.inresume = False
    
    
    #### Checks ####
    
    def checksnaps(self):
        if os.path.isfile("/usr/bin/snap"):
            self.allowmintupgrade.set_visible_child(self.builder.get_object('mintdescunavailable'))
            self.gotomintbtn.set_sensitive(False)
        else:
            self.allowmintupgrade.set_visible_child(self.builder.get_object('mintdescready'))
            self.gotomintbtn.set_sensitive(True)
    
    def checkforneon(self):
        if os.path.isfile("/usr/bin/enable-neon-ppa"):
            self.allowferentransition.set_visible_child(self.builder.get_object('cinn2plasdescunavailable'))
            self.gotoferenbtn.set_sensitive(False)
        else:
            self.allowferentransition.set_visible_child(self.builder.get_object('cinn2plasdescready'))
            self.gotoferenbtn.set_sensitive(True)
    
            
    #### Resuming Update ####
    def goto_resume(self):
        self.pagestack.set_visible_child(self.builder.get_object('pageupdatecontinue'))
        self.nextbtn.set_visible(False)
        self.updatebtn.set_visible(True)
        self.backbtn.set_visible(False)
        self.cancelbtn.set_sensitive(False)
        self.inresume = True
    
        
    #### Error Pages ####
    def goto_error(self):
        self.pagestack.set_visible_child(self.builder.get_object('pageerror'))
        self.nextbtn.set_visible(False)
        self.updatebtn.set_visible(False)
        self.backbtn.set_visible(False)
        self.cancelbtn.set_sensitive(False)
        self.builder.get_object('tryagainbtn').connect('clicked', self.error_response)
        
    def error_response(self, button):
        self.thread.join(0)
        self.goto_resume()
    
    
    #### Restart Page ####
    def auto_restart(self):
        import time
        secondspassed = 0
        while secondspassed <= 60:
            time.sleep(1)
            self.restarttimeleft.set_fraction(1.0 - ((1.0 / 60) * secondspassed))
            secondspassed += 1
        self.builder.get_object('restartnowbtn').set_sensitive(False)
        #When in doubt, just do it the other forced way
        os.system("/bin/systemctl reboot")
        time.sleep(20)
        
        #Restart GNOME-based DEs if all else fails
        os.system("/usr/bin/cinnamon-session-quit --reboot --no-prompt --force")
        os.system("/usr/bin/gnome-session-quit --reboot --no-prompt --force")
        #Restart Plasma as well if failing
        os.system("/usr/bin/qdbus org.kde.ksmserver /KSMServer logout 0 1 2")
        
    def goto_restart(self):
        if not self.systype == "classic":
            self.builder.get_object('restartlabel').set_visible_child(self.builder.get_object('restartlabelstandard'))
        else:
            self.builder.get_object('restartlabel').set_visible_child(self.builder.get_object('restartlabelclassic'))
        
        self.pagestack.set_visible_child(self.builder.get_object('page7'))
        self.thread = threading.Thread(target=self.auto_restart,
                                  args=())
        self.thread.start()
        
    
    #### Actual Update ####
    
    def feren_majorupdate_begin(self):
        pass
    
    def feren_cinn2plas_begin(self):
        self.grprogress.set_fraction(0.0)
        self.grstate.set_visible_child(self.builder.get_object('progressgettingready'))
        
        networkcheck = subprocess.Popen(["/usr/bin/nm-online"])
        networkcheck.communicate()[0]
        if networkcheck.returncode != 0:
            #Abort the update process
            self.pagestack.set_visible_child(self.builder.get_object('pageerrorinternet'))
            self.nextbtn.set_visible(False)
            self.updatebtn.set_visible(False)
            self.backbtn.set_visible(False)
            self.cancelbtn.set_sensitive(False)
            self.builder.get_object('tryagainbtn1').connect('clicked', self.error_response)
            return
        
        #Authenticate for the upgrade
        initialsuccess = subprocess.Popen(["/usr/bin/pkexec", "/usr/bin/feren-majorupdate-commands", "authenticate"])
        initialsuccess.communicate()[0]
        if initialsuccess.returncode != 0:
            #Abort the update process
            if self.inresume == False:
                self.pagestack.set_visible_child(self.builder.get_object('page4'))
                self.cancelbtn.set_sensitive(True)
                self.backbtn.set_visible(True)
                self.nextbtn.set_visible(False)
                self.updatebtn.set_visible(True)
            else:
                self.goto_resume()
            return
        
        #Transition with feren-cinn2plas code
        self.grprogress.set_fraction(0.95)
        
        self.grstate.set_visible_child(self.builder.get_object('progresstransitioning'))
        cinn2plascmd = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "ferencinn2plas"])
        cinn2plascmd.communicate()[0]
        if cinn2plascmd.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
        
        self.grprogress.set_fraction(1.0)
        self.goto_restart()
    
    def mint_transition_begin(self):
        self.lmswitchprogress.set_fraction(0.0)
        self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogresspreparing'))
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvertblank'))
        
        networkcheck = subprocess.Popen(["/usr/bin/nm-online"])
        networkcheck.communicate()[0]
        if networkcheck.returncode != 0:
            #Abort the update process
            self.pagestack.set_visible_child(self.builder.get_object('pageerrorinternet'))
            self.nextbtn.set_visible(False)
            self.updatebtn.set_visible(False)
            self.backbtn.set_visible(False)
            self.cancelbtn.set_sensitive(False)
            self.builder.get_object('tryagainbtn1').connect('clicked', self.error_response)
            return
        
        initialsuccess = subprocess.Popen(["/usr/bin/pkexec", "/usr/bin/feren-majorupdate-commands", "minttransition1", getpass.getuser()])
        self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogressbackingup'))
        initialsuccess.communicate()[0]
        if initialsuccess.returncode != 0:
            #Abort the update process
            if self.inresume == False:
                self.pagestack.set_visible_child(self.builder.get_object('page4mint'))
                self.cancelbtn.set_sensitive(True)
                self.backbtn.set_visible(True)
                self.nextbtn.set_visible(False)
                self.updatebtn.set_visible(True)
            else:
                self.goto_resume()
            return
        
        self.lmswitchprogress.set_fraction(0.2)
        
        self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogressremovingferen'))
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert1'))
        p2p1 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p1"])
        p2p1.communicate()[0]
        if p2p1.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.225)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert2'))
        p2p2 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p2"])
        p2p2.communicate()[0]
        if p2p2.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.25)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert3'))
        p2p3 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p3"])
        p2p3.communicate()[0]
        if p2p3.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.275)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert4'))
        p2p4 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p4"])
        p2p4.communicate()[0]
        if p2p4.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.3)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert5'))
        p2p5 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p5"])
        p2p5.communicate()[0]
        if p2p5.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.325)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert6'))
        p2p6 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p6"])
        p2p6.communicate()[0]
        if p2p6.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.35)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert7'))
        p2p7 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p7"])
        p2p7.communicate()[0]
        if p2p7.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.375)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvert8'))
        p2p8 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition2p8"])
        p2p8.communicate()[0]
        if p2p8.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.4)
        
        self.lmconvertstatus.set_visible_child(self.builder.get_object('mintconvertblank'))
        
        os.system("/usr/bin/feren-mint-transfer-userland")
        self.lmswitchprogress.set_fraction(0.5)
        
        self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogressinstallingmint'))
        p3 = subprocess.Popen(["/usr/bin/pkexec", "/usr/lib/feren-majorupdate/after-auth.sh", "minttransition3"])
        p3.communicate()[0]
        if p3.returncode != 0:
            #Abort the update process
            self.goto_error()
            return
            
        self.lmswitchprogress.set_fraction(0.6)
        
        self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogresupgradingmint'))
        #At this point all it is is just installing mintupgrade so if it fails it'll just go to the error messages in minttransitionupgruserland
        os.system("/usr/bin/pkexec /usr/lib/feren-majorupdate/after-auth.sh minttransition4")
        self.lmswitchprogress.set_fraction(0.8)
        
        self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogressfinalsteps'))
        time.sleep(5)
        os.system("/usr/bin/gsettings set org.gnome.Terminal.Legacy.Settings default-show-menubar false")
        finalpopen = subprocess.Popen(["/usr/bin/feren-terminal-launcher-temporary", "feren-majorupdate-commands", "minttransitionupgruserland"])
        os.system("/usr/bin/pkexec /usr/lib/feren-majorupdate/after-auth.sh minttransition5")
        finalpopen.communicate()[0]
        os.system("/usr/bin/gsettings reset org.gnome.Terminal.Legacy.Settings default-show-menubar")
        
        self.lmswitchprogress.set_fraction(1.0)
        
        Gtk.main_quit()
        
    
    #### Buttons ####
    
    def back_click(self, button):
        if self.pagestack.get_visible_child() == self.builder.get_object('page2'):
            self.pagestack.set_visible_child(self.builder.get_object('page1'))
            self.backbtn.set_visible(False)
            self.updatebtn.set_visible(False)
            return
        if self.pagestack.get_visible_child() == self.builder.get_object('page4') or self.pagestack.get_visible_child() == self.builder.get_object('page4mint'):
            if not self.systype == "classic":
                self.pagestack.set_visible_child(self.builder.get_object('page1'))
                self.backbtn.set_visible(False)
                self.nextbtn.set_visible(True)
            else:
                self.pagestack.set_visible_child(self.builder.get_object('page2'))
                self.nextbtn.set_visible(False)
            self.updatebtn.set_visible(False)
            return
    
    def next_click(self, button):
        if self.pagestack.get_visible_child() == self.builder.get_object('page1'):
            if not self.systype == "classic":
                self.pagestack.set_visible_child(self.builder.get_object('page4'))
                self.nextbtn.set_visible(False)
                self.updatebtn.set_visible(True)
            else:
                self.pagestack.set_visible_child(self.builder.get_object('page2'))
                self.updatebtn.set_visible(False)
                self.nextbtn.set_visible(False)
            self.backbtn.set_visible(True)
            return
    
    def update_click(self, button):
        self.cancelbtn.set_sensitive(False)
        self.backbtn.set_visible(False)
        self.nextbtn.set_visible(False)
        self.updatebtn.set_visible(False)
        
        if self.mintinstead == False and self.ferentransitioninstead == False:
            pass
        elif self.ferentransitioninstead == True:
            self.pagestack.set_visible_child(self.builder.get_object('page5'))
            self.grstate.set_visible_child(self.builder.get_object('progressgettingready'))
            self.thread = threading.Thread(target=self.feren_cinn2plas_begin,
                                  args=())
            self.thread.start()
        else:
            self.pagestack.set_visible_child(self.builder.get_object('pagemintswitching'))
            self.lmswitchstate.set_visible_child(self.builder.get_object('mintprogressbackingup'))
            self.thread = threading.Thread(target=self.mint_transition_begin,
                                  args=())
            self.thread.start()
    
    def timeshift_1_click(self, button):
        subprocess.Popen(["/usr/bin/pkexec", "/usr/bin/timeshift"])
        
    def transition_confirm_click(self, button):
        self.ferentransitioninstead = True
        self.mintinstead = False
        self.pagestack.set_visible_child(self.builder.get_object('page4'))
        self.nextbtn.set_visible(False)
        self.updatebtn.set_visible(True)
    
    def gotomint_confirm_click(self, button):
        #Set up Mint-specific pages first
        self.lmswitchstate = self.builder.get_object('lmswitchstate')
        self.lmswitchprogress = self.builder.get_object('lmswitchprogress')
        self.lmconvertstatus = self.builder.get_object('lmconvertprogress')
        
        
        self.ferentransitioninstead = False
        self.mintinstead = True
        self.pagestack.set_visible_child(self.builder.get_object('page4mint'))
        self.nextbtn.set_visible(False)
        self.updatebtn.set_visible(True)
        
    
    def restart_now(self, button):
        self.builder.get_object('restartnowbtn').set_sensitive(False)
        #When in doubt, just do it the other forced way
        os.system("/bin/systemctl reboot")
        time.sleep(20)
        
        #Restart GNOME-based DEs if all else fails
        os.system("/usr/bin/cinnamon-session-quit --reboot --no-prompt --force")
        os.system("/usr/bin/gnome-session-quit --reboot --no-prompt --force")
        #Restart Plasma as well if failing
        os.system("/usr/bin/qdbus org.kde.ksmserver /KSMServer logout 0 1 2")

    def cancel_click(self, button):
        Gtk.main_quit()
    

    #### SHOW APP ####
    def run(self):
        self.win.show_all()
        self.win.set_deletable(False)
        self.backbtn.set_visible(False)
        self.updatebtn.set_visible(False)
        if self.sysarch == "i686":
            self.nextbtn.set_visible(False)
            self.cancelbtn.grab_focus()
        else:
            self.nextbtn.grab_focus()
        if self.systype == "classic":
            self.checksnaps()
            self.checkforneon()
        #Open resume page for in-progress major updates
        if self.systype == "inprogressmint" or self.systype == "inprogress" or self.systype == "inprogresscinn2plas":
            if self.systype == "inprogressmint":
                self.mintinstead = True
                self.lmswitchstate = self.builder.get_object('lmswitchstate')
                self.lmswitchprogress = self.builder.get_object('lmswitchprogress')
                self.lmconvertstatus = self.builder.get_object('lmconvertprogress')
            elif self.systype == "inprogressferencinn2plas":
                self.ferentransitioninstead = True
            else:
                self.mintinstead = False
                self.ferentransitioninstead = False
            self.goto_resume()
        Gtk.main()

if __name__ == '__main__':
    usettings = init()
    usettings.run()
