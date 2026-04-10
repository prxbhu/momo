import os
import httpx

HA_URL = os.getenv("HOME_ASSISTANT_URL")
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")

def get_headers():
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

async def list_devices() -> str:
    """List all controllable smart home devices.
    Returns:
        Formatted list of device names, types, and current states
    """
    if not HA_URL or not HA_TOKEN:
         return "Home Assistant is not configured. Missing HOME_ASSISTANT_URL or HOME_ASSISTANT_TOKEN."
         
    try:
         async with httpx.AsyncClient() as client:
             res = await client.get(f"{HA_URL}/api/states", headers=get_headers(), timeout=10.0)
             res.raise_for_status()
             
             states = res.json()
             
             # Filter to controllable devices (lights, switches, climate, media_player)
             controllable_domains = {"light", "switch", "climate", "media_player"}
             devices = []
             
             for state in states:
                  entity_id = state.get("entity_id", "")
                  domain = entity_id.split(".")[0]
                  if domain in controllable_domains:
                       friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                       current_state = state.get("state", "unknown")
                       devices.append(f"- {friendly_name} ({entity_id}): {current_state}")
                       
             if not devices:
                  return "No controllable devices found."
                  
             return "Controllable devices:\n" + "\n".join(devices)
             
    except Exception as e:
         return f"Error getting Home Assistant devices: {e}"

async def control_device(device_id: str, action: str, value: str = None) -> str:
    """Control a smart home device.
    Args:
        device_id: Home Assistant entity ID (e.g. 'light.living_room')
        action: Action to perform (turn_on, turn_off, set_brightness, set_temperature, toggle)
        value: Optional value for the action (e.g. brightness level 0-255)
    Returns:
        Confirmation of the action performed
    """
    if not HA_URL or not HA_TOKEN:
         return "Home Assistant is not configured. Missing HOME_ASSISTANT_URL or HOME_ASSISTANT_TOKEN."
         
    domain = device_id.split(".")[0]
    service = action

    # Map some common aliases
    if action == "set_brightness":
         service = "turn_on"
         
    payload = {"entity_id": device_id}
    
    if value:
         if action == "set_brightness":
              payload["brightness"] = int(value)
         elif action == "set_temperature":
              payload["temperature"] = float(value)
              service = "set_temperature" # Usually handled by climate domain

    url = f"{HA_URL}/api/services/{domain}/{service}"
    
    try:
         async with httpx.AsyncClient() as client:
              res = await client.post(url, headers=get_headers(), json=payload, timeout=10.0)
              res.raise_for_status()
              
              return f"Successfully called {action} on {device_id}."
              
    except Exception as e:
         return f"Error controlling device {device_id}: {e}"
