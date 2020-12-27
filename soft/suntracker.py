#!/usr/bin/env python3
# -*- coding: utf8 -*-

import serial
import threading


class Gui(object):
    def __init__(self):
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

        buttonsframe = ttk.Frame(self.root, padding="3 3 3 3" )
        buttonsframe.grid(column=0, row=0, sticky="EW")

        mainframe = ttk.Frame(self.root, padding="3 3 12 12")
        mainframe.grid(column=0, row=1, sticky=(N, W, E, S))

        stateframe = ttk.Frame(self.root, padding="3 3 3 3")
        stateframe.grid(column=0, row=2, sticky="EW")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=10)
        self.root.rowconfigure(2, weight=1)

        mainframe.rowconfigure(0, weight=1)
        mainframe.rowconfigure(1, weight=4)
        mainframe.columnconfigure(0, weight=3)
        mainframe.columnconfigure(1, weight=3)
        mainframe.columnconfigure(2, weight=3)

        ttk.Button(buttonsframe, text="Open", command=self.open_port).grid(column=0, row=0, sticky=E)
        ttk.Button(buttonsframe, text="Close", command=self.close_port).grid(column=1, row=0, sticky=E)
        ''':todo rafraichir la liste des ports disponibles régulièrements, 
        message pour demander la sélection d'un port'''
        self.liste_ports = self.liste_ports_serie_disponibles()
        self.selected_port = ""
        ## Liste de choix des ports séries
        self.choices_ports_var = StringVar()
        self.lbox_ports = Listbox(mainframe, height=4, width=30, listvariable=self.choices_ports_var, selectmode="single")
        self.lbox_ports.grid(column=0, row=0, sticky='nsew')
        self.lbox_ports.bind("<<ListboxSelect>>", self.select_port)
        # Zone de texte des données reçues
        self.text_monitor = Text(mainframe, width=80, height=24)
        xs = ttk.Scrollbar(mainframe, orient='horizontal', command=self.text_monitor.xview)
        ys = ttk.Scrollbar(mainframe, orient='vertical', command=self.text_monitor.yview)
        self.text_monitor['xscrollcommand'] = xs.set
        self.text_monitor['yscrollcommand'] = ys.set
        self.text_monitor.grid(column=0, columnspan=3, row=1, sticky='nwes')
        ys.grid(column=4, row=1, sticky='ns')
        xs.grid(column=0, columnspan=3, sticky='ew')
        self.text_monitor.insert("1.0", "Les données reçues s'afficheront ici.\n")

        # Labels barre d'état
        self.texte_label_etat = StringVar()
        self.texte_label_etat.set("Aucun port sélectionné")
        label_etat = ttk.Label(stateframe, textvariable=self.texte_label_etat)
        label_etat.grid(column=0, row=0)

        self.root.bind("<<EVT_SERIALRX>>", self.OnSerialRead)
        self.root.bind("<Destroy>", self.OnDestroy)
        self.refresh_ports()

        # for child in mainframe.winfo_children():
        #     child.grid_configure(padx=5, pady=5)

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
            messagebox.showinfo(message="Sélectionner un port dans la liste déroulante")
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


if __name__ == "__main__":
    from tkinter import *
    from tkinter import ttk
    from tkinter import messagebox

    interface = Gui()
