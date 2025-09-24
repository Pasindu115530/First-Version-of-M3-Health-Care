"""
Auto-start management for Safe Warner with enable/disable controls
"""
import os
import sys
import platform
import subprocess
import warnings

class AutoStartManager:
    """Manage auto-start at system boot"""
    
    def __init__(self, app_name="SafeWarner"):
        self.app_name = app_name
        self.script_path = os.path.abspath(sys.argv[0])
        
    def set_auto_start(self, enabled: bool):
        """Enable or disable auto-start based on the flag"""
        system = platform.system()
        try:
            if system == "Windows":
                if enabled:
                    self._enable_windows_auto_start()
                else:
                    self._disable_windows_auto_start()
            elif system == "Darwin":
                if enabled:
                    self._enable_macos_auto_start()
                else:
                    self._disable_macos_auto_start()
            elif system == "Linux":
                if enabled:
                    self._enable_linux_auto_start()
                else:
                    self._disable_linux_auto_start()
            else:
                warnings.warn(f"Auto-start not supported on {system}")
        except Exception as e:
            print(f"Error setting auto-start: {e}")

    def is_auto_start_enabled(self) -> bool:
        """Check if auto-start is enabled on this system"""
        system = platform.system()
        try:
            if system == "Windows":
                import winreg
                key = winreg.HKEY_CURRENT_USER
                subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
                try:
                    with winreg.OpenKey(key, subkey, 0, winreg.KEY_READ) as reg_key:
                        value, _ = winreg.QueryValueEx(reg_key, self.app_name)
                        return isinstance(value, str) and len(value) > 0
                except FileNotFoundError:
                    return False
            elif system == "Darwin":
                plist_path = os.path.expanduser(f"~/Library/LaunchAgents/com.{self.app_name.lower()}.plist")
                return os.path.exists(plist_path)
            elif system == "Linux":
                desktop_path = os.path.expanduser(f"~/.config/autostart/{self.app_name}.desktop")
                return os.path.exists(desktop_path)
        except Exception:
            return False
        return False

    def _enable_windows_auto_start(self):
        """Enable auto-start on Windows"""
        try:
            import winreg
            
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.SetValueEx(reg_key, self.app_name, 0, winreg.REG_SZ, 
                                f'"{sys.executable}" "{self.script_path}" --auto-mode --minimal')
                
        except ImportError:
            # Fallback method
            startup_dir = os.path.join(os.getenv('APPDATA'), 
                                     'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            if os.path.exists(startup_dir):
                bat_path = os.path.join(startup_dir, f"{self.app_name}.bat")
                with open(bat_path, 'w') as f:
                    f.write(f'"{sys.executable}" "{self.script_path}" --auto-mode --minimal\n')

    def _disable_windows_auto_start(self):
        """Disable auto-start on Windows"""
        try:
            import winreg
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                try:
                    winreg.DeleteValue(reg_key, self.app_name)
                except FileNotFoundError:
                    pass
        except Exception:
            # Best-effort: remove fallback bat if present
            startup_dir = os.path.join(os.getenv('APPDATA'), 
                                     'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            bat_path = os.path.join(startup_dir, f"{self.app_name}.bat")
            if os.path.exists(bat_path):
                try:
                    os.remove(bat_path)
                except Exception:
                    pass
    
    def _enable_macos_auto_start(self):
        """Enable auto-start on macOS"""
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{self.app_name.lower()}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.script_path}</string>
        <string>--auto-mode</string>
        <string>--minimal</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>'''
        
        plist_path = os.path.expanduser(f"~/Library/LaunchAgents/com.{self.app_name.lower()}.plist")
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        
        with open(plist_path, 'w') as f:
            f.write(plist_content)
        
        # Load the launch agent
        subprocess.run(['launchctl', 'load', plist_path], capture_output=True)
    
    def _disable_macos_auto_start(self):
        """Disable auto-start on macOS"""
        plist_path = os.path.expanduser(f"~/Library/LaunchAgents/com.{self.app_name.lower()}.plist")
        try:
            subprocess.run(['launchctl', 'unload', plist_path], capture_output=True)
        except Exception:
            pass
        try:
            if os.path.exists(plist_path):
                os.remove(plist_path)
        except Exception:
            pass
    
    def _enable_linux_auto_start(self):
        """Enable auto-start on Linux"""
        desktop_file = f'''[Desktop Entry]
Type=Application
Name={self.app_name}
Exec={sys.executable} {self.script_path} --auto-mode --minimal
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
'''
        
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        
        desktop_path = os.path.join(autostart_dir, f"{self.app_name}.desktop")
        with open(desktop_path, 'w') as f:
            f.write(desktop_file)
        
        os.chmod(desktop_path, 0o755)

    def _disable_linux_auto_start(self):
        """Disable auto-start on Linux"""
        desktop_path = os.path.expanduser(f"~/.config/autostart/{self.app_name}.desktop")
        try:
            if os.path.exists(desktop_path):
                os.remove(desktop_path)
        except Exception:
            pass