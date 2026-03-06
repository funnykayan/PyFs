import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ensure local src imports work
sys.path.insert(0, os.path.dirname(__file__))
import fs


def default_container_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pyfs_data', 'fs.pyfs'))


class PyFsApp:
    def __init__(self, root):
        self.root = root
        self.root.title('PyFs')
        self.pfs = None
        self.password = None
        self._build_login()

    def _build_login(self):
        for w in self.root.winfo_children():
            w.destroy()
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text='Container file:').grid(row=0, column=0, sticky='w')
        self.path_var = tk.StringVar(value=default_container_path())
        path_entry = ttk.Entry(frm, textvariable=self.path_var, width=50)
        path_entry.grid(row=0, column=1, sticky='we')
        ttk.Button(frm, text='Browse', command=self._browse_container).grid(row=0, column=2, padx=6)

        ttk.Label(frm, text='Username:').grid(row=1, column=0, sticky='w')
        self.user_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.user_var).grid(row=1, column=1, columnspan=2, sticky='we')

        ttk.Label(frm, text='Password:').grid(row=2, column=0, sticky='w')
        self.pass_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.pass_var, show='*').grid(row=2, column=1, columnspan=2, sticky='we')

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text='Open / Create', command=self._open_container).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text='Quit', command=self.root.destroy).grid(row=0, column=1, padx=6)

        frm.columnconfigure(1, weight=1)

    def _browse_container(self):
        p = filedialog.asksaveasfilename(defaultextension='.pyfs', initialfile='fs.pyfs')
        if p:
            self.path_var.set(p)

    def _open_container(self):
        path = self.path_var.get()
        username = self.user_var.get().strip()
        password = self.pass_var.get()
        if not username or not password:
            messagebox.showerror('Error', 'Enter username and password')
            return
        pfs = fs.PyFS(path)
        try:
            if os.path.exists(path):
                pfs.load(username, password)
            else:
                # create new container
                pfs.create(username, password)
            self.pfs = pfs
            self.password = password
            self._build_manager()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _build_manager(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.title(f'PyFs - {os.path.basename(self.pfs.path)}')

        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill='both', expand=True)

        list_frame = ttk.Frame(frm)
        list_frame.pack(fill='both', expand=True)

        self.listbox = tk.Listbox(list_frame, height=15)
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side='left', fill='y')
        self.listbox.config(yscrollcommand=scrollbar.set)

        btns = ttk.Frame(frm)
        btns.pack(fill='x', pady=6)
        ttk.Button(btns, text='Import File', command=self._import_file).pack(side='left', padx=4)
        ttk.Button(btns, text='Export', command=self._export_file).pack(side='left', padx=4)
        ttk.Button(btns, text='Delete', command=self._delete_file).pack(side='left', padx=4)
        ttk.Button(btns, text='Refresh', command=self._refresh).pack(side='left', padx=4)
        ttk.Button(btns, text='Save & Logout', command=self._save_and_logout).pack(side='right', padx=4)

        self._refresh()

    def _refresh(self):
        self.listbox.delete(0, 'end')
        for name in self.pfs.list_files():
            self.listbox.insert('end', name)

    def _import_file(self):
        src = filedialog.askopenfilename()
        if not src:
            return
        name = os.path.basename(src)
        if name in self.pfs.list_files():
            if not messagebox.askyesno('Overwrite?', f'{name} exists — overwrite?'):
                return
        try:
            with open(src, 'rb') as f:
                data = f.read()
            self.pfs.add(name, data)
            self.pfs.save(self.password)
            self._refresh()
            messagebox.showinfo('Imported', f'{name} imported into container')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _export_file(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showerror('Error', 'No file selected')
            return
        name = self.listbox.get(sel[0])
        data = self.pfs.get(name)
        if data is None:
            messagebox.showerror('Error', 'File not found')
            return
        dest = filedialog.asksaveasfilename(initialfile=name)
        if not dest:
            return
        try:
            with open(dest, 'wb') as f:
                f.write(data)
            messagebox.showinfo('Exported', f'{name} exported to {dest}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _delete_file(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showerror('Error', 'No file selected')
            return
        name = self.listbox.get(sel[0])
        if not messagebox.askyesno('Confirm', f'Delete {name}?'):
            return
        try:
            self.pfs.delete(name)
            self.pfs.save(self.password)
            self._refresh()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _save_and_logout(self):
        try:
            self.pfs.save(self.password)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save: {e}')
            return
        self.pfs = None
        self.password = None
        self._build_login()


def main():
    root = tk.Tk()
    app = PyFsApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()


