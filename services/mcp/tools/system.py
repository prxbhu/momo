from datetime import datetime
import platform
import psutil

def get_current_time(timezone: str = "local") -> str:
    """Get the current date and time.
    Args:
        timezone: Timezone string (e.g. 'Asia/Kolkata', 'UTC', 'local')
    Returns:
        Current datetime as a readable string
    """
    now = datetime.now()
    # In a full implementation, we could use pytz or zoneinfo for specific timezones
    # For now, default to local system time.
    return now.strftime("%Y-%m-%d %H:%M:%S")

def get_system_info() -> str:
    """Get basic system information including CPU, RAM, disk usage.
    Returns:
        System stats as formatted text
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        
        # RAM
        memory = psutil.virtual_memory()
        ram_total = f"{memory.total / (1024 ** 3):.2f} GB"
        ram_used = f"{memory.used / (1024 ** 3):.2f} GB"
        ram_percent = memory.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_total = f"{disk.total / (1024 ** 3):.2f} GB"
        disk_used = f"{disk.used / (1024 ** 3):.2f} GB"
        disk_percent = disk.percent
        
        os_info = f"{platform.system()} {platform.release()}"
        
        # Wifi
        ssid = subprocess.check_output(["iwgetid", "-r"]).decode().strip()

        return (
             f"OS: {os_info}\n"
             f"CPU: {cpu_percent}% usage ({cpu_count} cores)\n"
             f"RAM: {ram_used} / {ram_total} ({ram_percent}%\n)"
             f"Disk: {disk_used} / {disk_total} ({disk_percent}%)\n"
             f"Wifi: {ssid}"    
        )
    except Exception as e:
         return f"Error retrieving system info: {e}"
