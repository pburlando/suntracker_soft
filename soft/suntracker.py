#!/usr/bin/env python3
# -*- coding: utf8 -*-
''':todo
Envoyer les commandes manuelles sur le port série
'''

import serial
import serial.tools.list_ports
import threading
from logzero import logger, logfile
from datetime import datetime
import os


class LogData:
    def __init__(self):
        dir_path = os.getcwd()
        now = datetime.now()
        logfile(dir_path + os.path.sep + now.strftime("%d-%m-%y_%H-%M-%S") + ".log")

    def LogLine(self, line):
        try:
            logger.info(line)
        except Exception as e:
            logger.error('{}: {})'.format(e.__class__.__name__, e))
            return e
        else:
            return 0


class Csv_data:
    def __init__(self):
        dir_path = os.getcwd()
        now = datetime.now()
        cur_time = now.strftime("%d-%m-%y_%H-%M-%S")
        self.file = f"{dir_path}{os.path.sep}datafile_{cur_time}.csv"
        self.create_csv_file()

    def create_csv_file(self):
        "Create a new CSV file and add the header row"
        with open(self.file, 'w') as f:
            header = "Date/time, lumg %, lumd %, Ecart G-D %, U_ppv V, I_ppv mA,  P_ppv mW, E_ppv J\n"
            f.write(header)

    def add_csv_data(self, data):
        """Add a row of data to the data_file CSV"""
        with open(self.file, 'a') as f:
            now = datetime.now()
            cur_time = now.strftime("%x %X.%f")
            f.write(f"{cur_time}, {data}\n")


class Gui(object):
    def __init__(self):
        """Construit l'interface graphique et le thread de lecture du port série"""
        # Attributs
        self.lumg = 0
        self.lumd = 0
        self.ecart_lum = 0
        self.u_ppv = 0
        self.i_ppv = 0
        self.p_ppv = 0
        self.Rcharge = 0
        self.energie = 0

        # Thread de lecture du port série
        self.serial = serial.Serial()
        self.serial.timeout = 0.5
        self.serial.baudrate = 9600
        self.thread = None
        self.alive = threading.Event()
        self.message = ""

        # GUI
        self.root = Tk()
        self.root.title("Suntracker monitor")
        self.buttons_manu_state = 1

        buttonsframe = ttk.Frame(self.root, padding="1 1 1 1")
        buttonsframe.grid(column=0, row=0, sticky="NWES")

        mainframe = ttk.Frame(self.root, padding="1 1 1 1")
        mainframe.grid(column=0, row=1, sticky="NWES")

        stateframe = ttk.Frame(self.root, padding="1 1 1 1")
        stateframe.grid(column=0, row=2, sticky="NWES")

        labelFrameManu = ttk.Labelframe(mainframe, text="Manuel")
        labelFrameManu.grid(row=0, column=1, sticky="NWES")

        labelFrameProd = ttk.Labelframe(mainframe, text="Production")
        labelFrameProd.grid(row=1, column=1, sticky="NWES")

        labelFramePosition = ttk.Labelframe(mainframe, text="Positionnement")
        labelFramePosition.grid(row=2, column=1, sticky="NWES")

        labelFrameConnexion = ttk.Labelframe(mainframe, text="Sélectionner une connexion")
        labelFrameConnexion.grid(row=0, column=0, sticky="NWES")

        labelFrameData = ttk.Labelframe(mainframe, text="Données reçues")
        labelFrameData.grid(row=1, column=0, rowspan=2, sticky="NWES")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=20)
        self.root.rowconfigure(1, weight=500)
        self.root.rowconfigure(2, weight=1)

        mainframe.rowconfigure(0, weight=1)
        mainframe.rowconfigure(1, weight=3)
        mainframe.rowconfigure(2, weight=1)
        mainframe.columnconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)

        stateframe.rowconfigure(0, weight=1)
        stateframe.rowconfigure(0, weight=1)

        buttonsframe.rowconfigure(0, weight=1)

        labelFrameConnexion.rowconfigure(0, weight=1)
        labelFrameConnexion.columnconfigure(0, weight=1)

        labelFrameData.rowconfigure(0, weight=1000)
        labelFrameData.rowconfigure(1, weight=1)
        labelFrameData.columnconfigure(0, weight=1000)
        labelFrameData.columnconfigure(1, weight=1)

        # Boutons menu
        ttk.Button(buttonsframe, text="Ouvrir", command=self.open_port).grid(column=0, row=0, sticky="WNS")
        ttk.Button(buttonsframe, text="Fermer", command=self.close_port).grid(column=1, row=0, sticky="WNS")
        ttk.Button(buttonsframe, text="Journal", command=self.log).grid(column=2, row=0, sticky="WNS")
        ttk.Button(buttonsframe, text="Aide", command=self.help).grid(column=3, row=0, sticky="WNS")
        # Liste de choix des ports séries
        self.liste_ports = self.liste_ports_serie_disponibles()
        self.selected_port = ""
        self.choices_ports_var = StringVar()
        self.lbox_ports = Listbox(labelFrameConnexion, height=4, width=30, listvariable=self.choices_ports_var,
                                  selectmode="single")
        self.lbox_ports.grid(column=0, row=0, sticky='nsew')

        # Zone de texte des données reçues
        self.text_monitor = Text(labelFrameData, width=80, height=24)
        xs = ttk.Scrollbar(labelFrameData, orient='horizontal', command=self.text_monitor.xview)
        ys = ttk.Scrollbar(labelFrameData, orient='vertical', command=self.text_monitor.yview)
        self.text_monitor['xscrollcommand'] = xs.set
        self.text_monitor['yscrollcommand'] = ys.set
        self.text_monitor.grid(column=0, row=0, sticky='nwes', ipady=5)
        ys.grid(column=1, row=0, sticky='ns')
        xs.grid(column=0, row=1, columnspan=2, sticky='ew')
        self.text_monitor.insert("1.0", "Les données reçues s'afficheront ici.\n")

        # Labels barre d'état
        self.texte_label_etat = StringVar()
        self.texte_label_etat.set("Aucun port sélectionné")
        label_etat = ttk.Label(stateframe, textvariable=self.texte_label_etat)
        label_etat.grid(column=0, row=0, sticky="NWES")

        # Labels production
        self.texte_label_u_ppv = StringVar()
        label_u_ppv = ttk.Label(labelFrameProd, textvariable=self.texte_label_u_ppv)
        label_u_ppv.grid(column=0, row=0, padx=5, pady=5, sticky='W')

        self.texte_label_i_ppv = StringVar()
        label_i_ppv = ttk.Label(labelFrameProd, textvariable=self.texte_label_i_ppv)
        label_i_ppv.grid(column=0, row=1, padx=5, pady=5, sticky='W')

        self.texte_label_p_ppv = StringVar()
        label_p_ppv = ttk.Label(labelFrameProd, textvariable=self.texte_label_p_ppv)
        label_p_ppv.grid(column=0, row=2, padx=5, pady=5, sticky='W')

        self.texte_label_r_charge = StringVar()
        label_r_ch = ttk.Label(labelFrameProd, textvariable=self.texte_label_r_charge)
        label_r_ch.grid(column=0, row=3, padx=5, pady=5, sticky='W')

        self.texte_label_energie = StringVar()
        label_energie = ttk.Label(labelFrameProd, textvariable=self.texte_label_energie)
        label_energie.grid(column=0, row=4, padx=5, pady=5, sticky='W')

        # labels positionnement
        self.texte_label_lumg = StringVar()
        label_lumg = ttk.Label(labelFramePosition, textvariable=self.texte_label_lumg)
        label_lumg.grid(column=0, row=0, padx=5, pady=5, sticky='W')

        self.texte_label_lumd = StringVar()
        label_lumd = ttk.Label(labelFramePosition, textvariable=self.texte_label_lumd)
        label_lumd.grid(column=0, row=1, padx=5, pady=5, sticky='W')

        self.texte_label_ecart_lum = StringVar()
        label_ecart_lum = ttk.Label(labelFramePosition, textvariable=self.texte_label_ecart_lum)
        label_ecart_lum.grid(column=0, row=2, padx=5, pady=5, sticky='W')

        # Définition des boutons du mode manuel
        names = ['Auto', 'Gauche', 'Droite']
        self.buttons_manuel = []
        self.text_buttons_manuel = []
        for i in range(len(names)):
            text_button = StringVar(value=names[i])
            button = ttk.Button(labelFrameManu, command=lambda i=i: self.callback_buttons(i), textvariable=text_button)
            if i != 0:
                button.state(['disabled'])
            button.grid(row=0, column=i)
            self.buttons_manuel.append(button)
            self.text_buttons_manuel.append(text_button)

        # Relier les événements à leur callback
        self.lbox_ports.bind("<<ListboxSelect>>", self.select_port)
        # self.root.bind("<<EVT_SERIALRX>>", self.OnSerialRead)
        self.root.bind("<<EVT_SERIALRX>>", lambda event: self.OnSerialRead(self.message))
        self.root.bind("<Destroy>", self.OnDestroy)
        self.root.focus_set()

        # Lancer la scrutation des ports disponibles
        self.refresh_ports()

        # Initialiser la journalisation
        self.log_data = LogData()

        # Initialiser l'enregistrement csv
        self.csv_data = Csv_data()

        # Autorisation données valides
        self.data_is_valid = False

        self.root.mainloop()

    def callback_buttons(self, i):
        button_states = ['Auto', 'Manu']
        if i == 0:
            self.text_buttons_manuel[i].set(button_states[self.buttons_manu_state])
            if self.buttons_manu_state == 1:
                self.buttons_manuel[1].state(['!disabled'])
                self.buttons_manuel[2].state(['!disabled'])
            else:
                self.buttons_manuel[1].state(['disabled'])
                self.buttons_manuel[2].state(['disabled'])

            self.buttons_manu_state = not self.buttons_manu_state
        elif i == 1:
            print("Commande panneau vers la gauche")
        elif i == 2:
            print("Commande panneau vers la droite")

    def liste_ports_serie_disponibles(self):
        """
        Debian buster
        liste les ports séries disponibles par identificateur
        et renvoie une liste
        """
        ports = serial.tools.list_ports.comports()
        return [port for port, desc, hwid in sorted(ports)]

    def refresh_ports(self):
        """Refresh availables ports in lbox_ports every 5s"""
        self.liste_ports = self.liste_ports_serie_disponibles()
        self.choices_ports_var.set(self.liste_ports)
        self.root.after(5000, self.refresh_ports)

    def select_port(self, *args):
        index = self.lbox_ports.curselection()
        index = int(index[0])
        self.selected_port = self.liste_ports[index]
        self.texte_label_etat.set(f"{self.selected_port}, 9600 bauds")

    def open_port(self, *args):
        if self.selected_port == "":
            messagebox.showinfo(message="Sélectionner un port dans la liste connexions")
            return -1
        if self.serial.isOpen():
            messagebox.showinfo(message="Le port est déjà ouvert")
            return -1
        # Lancer l'écoute du port série
        self.serial.port = self.selected_port
        try:
            self.serial.open()
        except serial.SerialException as e:
            messagebox.showerror(message=f"Erreur: {e}")
        else:
            self.text_monitor.delete('1.0', 'end')
            self.texte_label_etat.set(f"{self.selected_port}, 9600 bauds, en réception")
            # Démarrer la journalisation
            self.StartThread()
        return 0

    def close_port(self):
        self.StopThread()
        try:
            self.serial.close()
        except serial.SerialException as e:
            messagebox.showerror(message=f"Erreur: {e}")
            self.texte_label_etat.set("")
        else:
            self.texte_label_etat.set(f"{self.selected_port}, fermé")
            self.texte_label_lumg.set(f"Luminosité capteur gauche = --- %")
            self.texte_label_lumd.set(f"Luminosité capteur droit = --- %")
            self.texte_label_ecart_lum.set(f"Ecart gauche - droit  = --- %")
            self.texte_label_u_ppv.set(f"Uppv = --- V")
            self.texte_label_i_ppv.set(f"Ippv = --- mA")
            self.texte_label_p_ppv.set(f"Pppv = --- mW")
            self.texte_label_r_charge.set(f"Rcharge = --- \N{GREEK CAPITAL LETTER OMEGA}")
            self.texte_label_energie.set("Energie = --- J")
            self.energie = 0
        finally:
            self.data_is_valid = False
        return 0

    def StartThread(self):
        """Start the receiver thread"""
        self.thread = threading.Thread(target=self.ComPortThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        self.serial.rts = True
        self.serial.dtr = True

    def StopThread(self):
        """Stop the receiver thread, wait until it's finished."""
        if self.thread is not None:
            self.alive.clear()  # clear alive event for thread
            self.thread.join(timeout=2)  # wait until thread has finished
            self.thread = None

    def ComPortThread(self):
        """\
        Thread that handles the incoming traffic. Does the basic input
        transformation (newlines) and generates an SerialRxEvent
        """
        while self.alive.isSet():
            try:
                line = self.serial.readline()
            except serial.SerialException as e:
                messagebox.showerror(message=f"Erreur: {e}")
                line = None
                self.close_port()
                self.texte_label_etat.set("Connexion perdue")

            if line:
                self.message = line.decode().strip('\r\n') + '\n'
                if "Démarrage" in self.message:
                    self.data_is_valid = True
                if self.data_is_valid:
                    self.root.event_generate("<<EVT_SERIALRX>>")

    def OnSerialRead(self, data):
        self.text_monitor.insert('end', data)
        self.text_monitor.see('end')
        self.data_compute(data)
        self.log_data.LogLine(data)  # Log des données entrantes
        # self.csv_data.add_csv_data(data)

    def OnDestroy(self, event):
        self.close_port()

    def log(self):
        '''Proposer l'ouverture d'un fichier de log ou csv puis l'ouvrir avec l'éditeur de texte par défaut'''
        filename = filedialog.askopenfilename()

    @staticmethod
    def help():
        print("help")

    def data_compute(self, line):
        data = line.split(',')
        if len(data) == 7:
            raw_data = [float(val.strip()) for val in data[0:4]]
            self.lumg = raw_data[0] * 100 / 1024
            self.lumd = raw_data[1] * 100 / 1024
            self.ecart_lum = self.lumg - self.lumd

            self.u_ppv = raw_data[2] * 5 * 9.81 / 1024 / 2

            self.i_ppv = -0.5725 * raw_data[3] + 367
            if self.i_ppv < 0:
                self.i_ppv = 0
            self.p_ppv = self.u_ppv * self.i_ppv

            self.energie += self.p_ppv / 1000  # Energie calculée en Joule

            csv_data = f"{self.lumg:.1f}, {self.lumd:.1f}, {self.ecart_lum:.1f}, {self.u_ppv:.2f}," \
                       f"{self.i_ppv:.2f}, {self.p_ppv:.2f}, {self.energie:.2f}"
            self.csv_data.add_csv_data(csv_data)
            self.print_data()

    def print_data(self):
        ''' Affiche les données dans le labelFrame data'''
        self.texte_label_lumg.set(f"Luminosité capteur gauche = {self.lumg:.1f} %")
        self.texte_label_lumd.set(f"Luminosité capteur droit = {self.lumd:.1f} %")
        self.texte_label_ecart_lum.set(f"Ecart gauche - droit  = {self.ecart_lum:.1f} %")
        self.texte_label_u_ppv.set(f"Uppv = {self.u_ppv:.2f} V")
        self.texte_label_i_ppv.set(f"Ippv = {self.i_ppv:.2f} mA")
        self.texte_label_p_ppv.set(f"Pppv = {self.p_ppv:.2f} mW")
        self.texte_label_energie.set(f"Energie = {self.energie:.2f} J")
        if self.i_ppv >= 5 and self.u_ppv >= 2:
            self.Rcharge = self.u_ppv / self.i_ppv
            self.texte_label_r_charge.set(f"Rcharge = {self.Rcharge:.2f} \N{GREEK CAPITAL LETTER OMEGA}")
        else:
            self.Rcharge = "---"
            self.texte_label_r_charge.set(f"Rcharge = {self.Rcharge} \u03A9")


if __name__ == "__main__":
    from tkinter import *
    from tkinter import ttk
    from tkinter import messagebox
    from tkinter import filedialog

    interface = Gui()
