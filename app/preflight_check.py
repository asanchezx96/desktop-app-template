"""
preflight_check.py — Verificación de requisitos del sistema.

Muestra un diálogo WinForms nativo con el estado de cada componente:
  ✔  .NET Framework 4.6.2+
  ✔  System.Windows.Forms (CLR)
  ✔  Microsoft Edge WebView2 Runtime

Si todo está OK, retorna silenciosamente.
Si algo falta, muestra el diálogo con links de descarga y botón de auto-instalación.
"""

import os
import sys
import webbrowser


# ══════════════════════════════════════════════════════════════════════════
#  CHECKS
# ══════════════════════════════════════════════════════════════════════════

def _check_dotnet_framework():
    """Verifica .NET Framework 4.6.2+ via registro de Windows."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
        ) as key:
            release, _ = winreg.QueryValueEx(key, 'Release')
            version_map = [
                (533320, "4.8.1"), (528040, "4.8"), (461808, "4.7.2"),
                (461308, "4.7.1"), (460798, "4.7"), (394802, "4.6.2"),
            ]
            for min_release, version in version_map:
                if release >= min_release:
                    return True, version
    except Exception:
        pass
    return False, "No instalado"


def _check_winforms():
    """Verifica que System.Windows.Forms se pueda cargar via CLR."""
    try:
        import clr
        clr.AddReference('System.Windows.Forms')
        return True, "OK"
    except Exception as e:
        return False, str(e)[:60]


def _check_webview2():
    """Verifica Microsoft Edge WebView2 Runtime via registro."""
    try:
        import winreg
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'),
        ]
        for hive, path in keys:
            try:
                with winreg.OpenKey(hive, path) as key:
                    ver, _ = winreg.QueryValueEx(key, 'pv')
                    if ver and ver != '0.0.0.0':
                        return True, ver
            except (OSError, FileNotFoundError):
                continue
    except Exception:
        pass
    return False, "No instalado"


# ══════════════════════════════════════════════════════════════════════════
#  INSTALADOR WEBVIEW2
# ══════════════════════════════════════════════════════════════════════════

def _install_webview2_sync():
    """Descarga e instala WebView2 Runtime (síncrono)."""
    import subprocess
    import tempfile

    url = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "MicrosoftEdgeWebview2Setup.exe")

    subprocess.run(
        ['powershell', '-Command',
         f"Invoke-WebRequest -Uri '{url}' -OutFile '{path}'"],
        timeout=120, check=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )

    subprocess.run(
        [path, '/silent', '/install'],
        timeout=180, check=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )


# ══════════════════════════════════════════════════════════════════════════
#  DIÁLOGO WINFORMS
# ══════════════════════════════════════════════════════════════════════════

def _show_dialog(checks):
    """Muestra el diálogo de verificación usando WinForms nativo."""
    import clr
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')

    # pyrefly: ignore [missing-import]
    import System.Windows.Forms as WF
    # pyrefly: ignore [missing-import]
    from System.Drawing import Color, Font, FontStyle, Size, Point
    # pyrefly: ignore [missing-import]
    from System import EventHandler

    WF.Application.EnableVisualStyles()

    result = [False]

    # ── Form ──
    form = WF.Form()
    form.Text = "Verificación de Requisitos del Sistema"
    form.StartPosition = WF.FormStartPosition.CenterScreen
    form.FormBorderStyle = WF.FormBorderStyle.FixedDialog
    form.MaximizeBox = False
    form.MinimizeBox = False
    form.TopMost = True
    form.BackColor = Color.FromArgb(250, 250, 252)

    # ── Fonts ──
    f_title  = Font("Segoe UI", 13, FontStyle.Bold)
    f_sub    = Font("Segoe UI", 8.5)
    f_item   = Font("Segoe UI", 10)
    f_item_b = Font("Segoe UI", 10, FontStyle.Bold)
    f_link   = Font("Segoe UI", 8.5)
    f_btn    = Font("Segoe UI", 9.5, FontStyle.Bold)
    f_btn_sm = Font("Segoe UI", 9)

    # ── Header panel ──
    hdr = WF.Panel()
    hdr.Dock = WF.DockStyle.Top
    hdr.Height = 65
    hdr.BackColor = Color.FromArgb(13, 15, 20)
    form.Controls.Add(hdr)

    lbl_t = WF.Label()
    lbl_t.Text = "Verificación de Requisitos"
    lbl_t.Font = f_title
    lbl_t.ForeColor = Color.White
    lbl_t.Location = Point(22, 10)
    lbl_t.AutoSize = True
    hdr.Controls.Add(lbl_t)

    lbl_s = WF.Label()
    lbl_s.Text = "Comprobando componentes necesarios para ejecutar la aplicación"
    lbl_s.Font = f_sub
    lbl_s.ForeColor = Color.FromArgb(140, 150, 165)
    lbl_s.Location = Point(22, 38)
    lbl_s.AutoSize = True
    hdr.Controls.Add(lbl_s)

    # ── Check items ──
    y = 85
    GREEN  = Color.FromArgb(34, 139, 34)
    RED    = Color.FromArgb(200, 30, 30)
    BLUE   = Color.FromArgb(0, 120, 212)
    GRAY   = Color.Gray

    btn_continue_ref = [None]

    for chk in checks:
        ok = chk['ok']
        icon = "\u2714" if ok else "\u2718"       # ✔ / ✘
        color = GREEN if ok else RED

        # ── Nombre del componente ──
        lbl_name = WF.Label()
        lbl_name.Text = f"  {icon}   {chk['name']}"
        lbl_name.Font = f_item_b if not ok else f_item
        lbl_name.ForeColor = color
        lbl_name.Location = Point(24, y)
        lbl_name.AutoSize = True
        form.Controls.Add(lbl_name)

        # ── Versión / estado ──
        lbl_ver = WF.Label()
        lbl_ver.Text = chk['info']
        lbl_ver.Font = f_sub
        lbl_ver.ForeColor = GRAY if ok else Color.FromArgb(170, 50, 50)
        lbl_ver.Location = Point(400, y + 3)
        lbl_ver.AutoSize = True
        form.Controls.Add(lbl_ver)

        y += 32

        # ── Si falla: link de descarga ──
        if not ok and chk.get('url'):
            link = WF.LinkLabel()
            link.Text = f"       Descargar:  {chk['url']}"
            link.Font = f_link
            link.Location = Point(32, y)
            link.AutoSize = True
            url_val = chk['url']
            link.LinkClicked += lambda s, e, u=url_val: webbrowser.open(u)
            form.Controls.Add(link)
            y += 24

            # ── Botón de auto-instalación (solo WebView2) ──
            if chk.get('auto_install'):
                btn_inst = WF.Button()
                btn_inst.Text = "\u2B07  Instalar automáticamente"
                btn_inst.Font = f_btn_sm
                btn_inst.Size = Size(240, 34)
                btn_inst.Location = Point(44, y)
                btn_inst.BackColor = BLUE
                btn_inst.ForeColor = Color.White
                btn_inst.FlatStyle = WF.FlatStyle.Flat
                btn_inst.FlatAppearance.BorderSize = 0
                btn_inst.Cursor = WF.Cursors.Hand

                # Guardar refs para el closure
                _name_lbl = lbl_name
                _ver_lbl  = lbl_ver
                _chk      = chk

                def make_install_handler(btn, name_l, ver_l, c):
                    def handler(sender, event):
                        btn.Enabled = False
                        btn.Text = "\u23F3  Descargando WebView2..."
                        form.Cursor = WF.Cursors.WaitCursor
                        form.Refresh()

                        try:
                            _install_webview2_sync()

                            # Éxito: actualizar UI
                            btn.Text = "\u2714  Instalado correctamente"
                            btn.BackColor = GREEN
                            name_l.Text = f"  \u2714   {c['name']}"
                            name_l.ForeColor = GREEN
                            name_l.Font = f_item
                            ver_l.Text = "Instalado"
                            ver_l.ForeColor = GRAY
                            c['ok'] = True

                            # Habilitar "Continuar" si todo pasó
                            if all(ch['ok'] for ch in checks) and btn_continue_ref[0]:
                                btn_continue_ref[0].Enabled = True
                                btn_continue_ref[0].BackColor = BLUE

                        except Exception as ex:
                            btn.Text = f"\u2718  Error: {str(ex)[:35]}"
                            btn.BackColor = RED
                            btn.Enabled = True

                        form.Cursor = WF.Cursors.Default
                        form.Refresh()

                    return handler

                btn_inst.Click += EventHandler(
                    make_install_handler(btn_inst, _name_lbl, _ver_lbl, _chk)
                )
                form.Controls.Add(btn_inst)
                y += 42

        y += 16  # Espaciado entre checks

    # ── Separador ──
    sep = WF.Panel()
    sep.Location = Point(20, y)
    sep.Size = Size(510, 1)
    sep.BackColor = Color.FromArgb(215, 218, 224)
    form.Controls.Add(sep)
    y += 20

    # ── Botones de acción ──
    all_ok = all(c['ok'] for c in checks)

    btn_cont = WF.Button()
    btn_cont.Text = "Continuar"
    btn_cont.Font = f_btn
    btn_cont.Size = Size(130, 40)
    btn_cont.Location = Point(270, y)
    btn_cont.BackColor = BLUE if all_ok else Color.FromArgb(180, 183, 190)
    btn_cont.ForeColor = Color.White
    btn_cont.FlatStyle = WF.FlatStyle.Flat
    btn_cont.FlatAppearance.BorderSize = 0
    btn_cont.Enabled = all_ok
    btn_cont.Cursor = WF.Cursors.Hand
    btn_continue_ref[0] = btn_cont

    def _on_continue(s, e):
        result[0] = True
        form.Close()

    btn_cont.Click += EventHandler(_on_continue)
    form.Controls.Add(btn_cont)

    btn_exit = WF.Button()
    btn_exit.Text = "Salir"
    btn_exit.Font = Font("Segoe UI", 9.5)
    btn_exit.Size = Size(100, 40)
    btn_exit.Location = Point(410, y)
    btn_exit.BackColor = Color.FromArgb(242, 242, 245)
    btn_exit.ForeColor = Color.FromArgb(50, 50, 55)
    btn_exit.FlatStyle = WF.FlatStyle.Flat
    btn_exit.FlatAppearance.BorderSize = 1
    btn_exit.FlatAppearance.BorderColor = Color.FromArgb(200, 202, 208)
    btn_exit.Cursor = WF.Cursors.Hand

    def _on_exit(s, e):
        result[0] = False
        form.Close()

    btn_exit.Click += EventHandler(_on_exit)
    form.Controls.Add(btn_exit)

    # ── Ajustar tamaño del form ──
    form.ClientSize = Size(550, y + 65)

    # ── Mostrar ──
    form.ShowDialog()
    form.Dispose()

    return result[0]


# ══════════════════════════════════════════════════════════════════════════
#  ENTRADA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def run_preflight():
    """
    Ejecuta todas las verificaciones.
    - Si todo OK → retorna True silenciosamente (sin diálogo).
    - Si algo falta → muestra diálogo con estado, links e instalador.
    - Retorna True (continuar) o False (salir).
    """

    # 1) Verificar si podemos usar WinForms
    winforms_ok, winforms_info = _check_winforms()

    if not winforms_ok:
        # Sin WinForms no podemos mostrar el diálogo bonito → MessageBox básico
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "No se pudo cargar System.Windows.Forms.\n\n"
            "Verifica que .NET Framework 4.6.2+ esté habilitado:\n"
            "  Panel de Control → Programas →\n"
            "  Activar o desactivar características de Windows\n\n"
            "O descarga desde:\n"
            "https://dotnet.microsoft.com/download/dotnet-framework\n\n"
            f"Error: {winforms_info}",
            "Error - Verificación de Requisitos",
            0x10,
        )
        return False

    # 2) Ejecutar todas las verificaciones
    dotnet_ok, dotnet_info     = _check_dotnet_framework()
    webview2_ok, webview2_info = _check_webview2()

    checks = [
        {
            'name': '.NET Framework 4.6.2+',
            'ok': dotnet_ok,
            'info': f"v{dotnet_info}" if dotnet_ok else dotnet_info,
            'url': 'https://dotnet.microsoft.com/download/dotnet-framework',
        },
        {
            'name': 'System.Windows.Forms (CLR)',
            'ok': winforms_ok,
            'info': winforms_info,
            'url': None,
        },
        {
            'name': 'Microsoft Edge WebView2 Runtime',
            'ok': webview2_ok,
            'info': f"v{webview2_info}" if webview2_ok else webview2_info,
            'url': 'https://developer.microsoft.com/microsoft-edge/webview2/',
            'auto_install': True,
        },
    ]

    # 3) Si todo OK → continuar sin mostrar nada
    if all(c['ok'] for c in checks):
        return True

    # 4) Mostrar diálogo con resultados
    return _show_dialog(checks)
