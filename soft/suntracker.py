#!/usr/bin/env python3
# -*- coding: utf8 -*-

import serial
import threading


class Gui(object):
    def __init__(self):
        """Construit l'interface graphique et le thread de lecture du port série"""
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

        buttonsframe = ttk.Frame(self.root, padding="1 1 1 1" )
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
        self.lbox_ports = Listbox(labelFrameConnexion, height=4, width=30, listvariable=self.choices_ports_var, selectmode="single")
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


        # Relier les événements à leur callback
        self.lbox_ports.bind("<<ListboxSelect>>", self.select_port)
        self.root.bind("<<EVT_SERIALRX>>", self.OnSerialRead)
        self.root.bind("<Destroy>", self.OnDestroy)

        # Lancer la scrutation des ports disponibles
        self.refresh_ports()



        self.root.mainloop()

    def liste_ports_serie_disponibles(self):
        """
        Debian buster
        liste les ports séries disponibles par identificateur
        et renvoie une liste
        """
        from subprocess import run
        devices = run(["ls", "/dev/serial/by-id"], capture_output=True)
        return devices.stdout.decode().split('\n')

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
        self.serial.port = f"/dev/serial/by-id/{self.selected_port}"
        try:
            self.serial.open()
        except serial.SerialException as e:
            messagebox.showerror(message=f"Erreur: {e}")
        else:
            self.text_monitor.delete('1.0', 'end')
            self.texte_label_etat.set(f"{self.selected_port}, 9600 bauds, en réception")
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
        return 0

    def StartThread(self):
        """Start the receiver thread"""
        self.thread = threading.Thread(target=self.ComPortThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()
        #self.serial.rts = True
        #self.serial.dtr = True

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
                self.root.event_generate("<<EVT_SERIALRX>>")

    def OnSerialRead(self, event):
        self.text_monitor.insert('end', self.message)
        self.text_monitor.see('end')

    def OnDestroy(self, event):
        self.close_port()

    def log(self):
        print("log")

    def help(self):
        print("help")


if __name__ == "__main__":
    from tkinter import *
    from tkinter import ttk
    from tkinter import messagebox

    interface = Gui()
