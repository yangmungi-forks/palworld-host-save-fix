import json
import os
import subprocess
import sys
import zlib

import save_opener

UESAVE_TYPE_MAPS = [
    ".worldSaveData.CharacterSaveParameterMap.Key=Struct",
    ".worldSaveData.FoliageGridSaveDataMap.Key=Struct",
    ".worldSaveData.FoliageGridSaveDataMap.ModelMap.InstanceDataMap.Key=Struct",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Key=Struct",
    ".worldSaveData.ItemContainerSaveData.Key=Struct",
    ".worldSaveData.CharacterContainerSaveData.Key=Struct",
]

def main():
    if len(sys.argv) < 6:
        print('fix-host-save.py <uesave.exe> <save_path> <new_guid> <old_guid> <guild_fix>')
        exit(1)
    
    uesave_path = sys.argv[1]
    save_path = sys.argv[2]
    new_guid = sys.argv[3]
    old_guid = sys.argv[4]
    guild_fix = sys.argv[5]
    
    # String to boolean.
    if guild_fix.lower() == 'true':
        guild_fix = True
    elif guild_fix.lower() == 'false':
        guild_fix = False
    else:
        print('ERROR: Invalid <guild_fix> argument. It should be either "True" or "False".')
        exit(1)
    
    # Users accidentally include the .sav file extension when copying the GUID over. Only the GUID should be passed.
    if new_guid[-4:] == '.sav' or old_guid[-4:] == '.sav':
        print('ERROR: It looks like you\'re providing the whole name of the file instead of just the GUID. For example, instead of using "<GUID>.sav" in the command, you should be using only the GUID.')
        exit(1)
    
    # Users accidentally remove characters from their GUIDs when copying it over. All GUIDs should be 32 characters long.
    if len(new_guid) != 32:
        print('ERROR: Your <new_guid> should be 32 characters long, but it is ' + str(len(new_guid)) + ' characters long. Make sure you copied the exact GUID.')
        exit(1)
    
    if len(old_guid) != 32:
        print('ERROR: Your <old_guid> should be 32 characters long, but it is ' + str(len(old_guid)) + ' characters long. Make sure you copied the exact GUID.')
        exit(1)
    
    # Apply expected formatting for the GUID.
    new_guid_formatted = '{}-{}-{}-{}-{}'.format(new_guid[:8], new_guid[8:12], new_guid[12:16], new_guid[16:20], new_guid[20:]).lower()
    
    level_sav_path = save_path + '/Level.sav'
    old_sav_path = save_path + '/Players/'+ old_guid + '.sav'
    new_sav_path = save_path + '/Players/' + new_guid + '.sav'
    level_json_path = level_sav_path + '.json'
    old_json_path = old_sav_path + '.json'

    # uesave_path must point directly to the executable, not just the path it is located in.
    if not os.path.exists(uesave_path) or not os.path.isfile(uesave_path):
        print('ERROR: Your given <uesave_path> of "' + uesave_path + '" is invalid. It must point directly to the executable. For example: C:\\Users\\Bob\\.cargo\\bin\\uesave.exe')
        exit(1)
    
    # save_path must exist in order to use it.
    if not os.path.exists(save_path):
        print('ERROR: Your given <save_path> of "' + save_path + '" does not exist. Did you enter the correct path to your save folder?')
        exit(1)
    
    # The player needs to have created a character on the dedicated server and that save is used for this script.
    if not os.path.exists(new_sav_path):
        print('ERROR: Your player save does not exist. Did you enter the correct new GUID of your player? It should look like "8E910AC2000000000000000000000000".\nDid your player create their character with the provided save? Once they create their character, a file called "' + new_sav_path + '" should appear. Look back over the steps in the README on how to get your new GUID.')
        exit(1)
    
    # Warn the user about potential data loss.
    print('WARNING: Running this script WILL change your save files and could \
potentially corrupt your data. It is HIGHLY recommended that you make a backup \
of your save folder before continuing. Press enter if you would like to continue.')
    input('> ')
    
    if guild_fix:
        old_level_formatted = ''
        new_level_formatted = ''
        
        # Player GUIDs in a guild are stored as the decimal representation of their GUID.
        # Every byte in decimal represents 2 hexidecimal characters of the GUID
        # 32-bit little endian.
        for y in range(8, 36, 8):
            for x in range(y-1, y-9, -2):
               temp_old = str(int(old_guid[x-1] + old_guid[x], 16))+',\n'
               temp_new = str(int(new_guid[x-1] + new_guid[x], 16))+',\n'
               old_level_formatted += temp_old
               new_level_formatted += temp_new
            
        old_level_formatted = old_level_formatted.rstrip("\n,")
        new_level_formatted = new_level_formatted.rstrip("\n,")
        old_level_formatted = list(map(int, old_level_formatted.split(",\n")))
        new_level_formatted = list(map(int, new_level_formatted.split(",\n")))
    
    # Convert save files to JSON so it is possible to edit them.
    print('Converting save files to JSON...', flush=True)
    sav_to_json(uesave_path, level_sav_path)
    sav_to_json(uesave_path, old_sav_path)
    print('Done!', flush=True)
    
    # Parse our JSON files.
    print('Parsing JSON files...', end='', flush=True)
    with open(old_json_path) as f:
        old_json = json.load(f)
    with open(level_json_path) as f:
        level_json = json.load(f)
    print('Done!', flush=True)
    
    # Replace all instances of the old GUID with the new GUID.
    print('Modifying JSON save data...', end='', flush=True)
    
    # Player data replacement.
    old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"]["PlayerUId"]["Struct"]["value"]["Guid"] = new_guid_formatted
    old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"]["IndividualId"]["Struct"]["value"]["Struct"]["PlayerUId"]["Struct"]["value"]["Guid"] = new_guid_formatted
    old_instance_id = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"]["IndividualId"]["Struct"]["value"]["Struct"]["InstanceId"]["Struct"]["value"]["Guid"]
    
    # Level data replacement.
    instance_ids_len = len(level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"]["Map"]["value"])
    for i in range(instance_ids_len):
        instance_id = level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"]["Map"]["value"][i]["key"]["Struct"]["Struct"]["InstanceId"]["Struct"]["value"]["Guid"]
        if instance_id == old_instance_id:
            level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"]["Map"]["value"][i]["key"]["Struct"]["Struct"]["PlayerUId"]["Struct"]["value"]["Guid"] = new_guid_formatted
            break
    
    if guild_fix:
        # Guild data replacement.
        group_ids_len = len(level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["GroupSaveDataMap"]["Map"]["value"])
        for i in range(group_ids_len):
            group_id = level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["GroupSaveDataMap"]["Map"]["value"][i]
            if group_id["value"]["Struct"]["Struct"]["GroupType"]["Enum"]["value"] == "EPalGroupType::Guild":
                group_raw_data = group_id["value"]["Struct"]["Struct"]["RawData"]["Array"]["value"]["Base"]["Byte"]["Byte"]
                raw_data_len = len(group_raw_data)
                for j in range(raw_data_len-15):
                    if group_raw_data[j:j+16] == old_level_formatted:
                        group_raw_data[j:j+16] = new_level_formatted
    print('Done!', flush=True)
    
    # Dump modified data to JSON.
    print('Exporting JSON data...', end='', flush=True)
    with open(old_json_path, 'w') as f:
        json.dump(old_json, f, indent=2)
    with open(level_json_path, 'w') as f:
        json.dump(level_json, f, indent=2)
    print('Done!')
    
    # Convert our JSON files to save files.
    print('Converting JSON files back to save files...', flush=True)
    json_to_sav(uesave_path, level_json_path)
    json_to_sav(uesave_path, old_json_path)
    print('Done!', flush=True)
    
    # Clean up miscellaneous GVAS and JSON files which are no longer needed.
    print('Cleaning up miscellaneous files...', end='', flush=True)
    clean_up_files(level_sav_path)
    clean_up_files(old_sav_path)
    print('Done!', flush=True)
    
    # We must rename the patched save file from the old GUID to the new GUID for the server to recognize it.
    if os.path.exists(new_sav_path):
        os.remove(new_sav_path)
    os.rename(old_sav_path, new_sav_path)
    print('Fix has been applied! Have fun!')

def sav_to_json(uesave_path, file):
    save_opener.sav_to_json(uesave_path, file)

def json_to_sav(uesave_path, file):
    save_opener.json_to_sav(uesave_path, file)

def clean_up_files(file):
    os.remove(file + '.json')
    os.remove(file + '.gvas')
    
if __name__ == "__main__":
    main()
