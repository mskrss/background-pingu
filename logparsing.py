#!/usr/bin/env python
# coding: utf-8

import re
import requests
from packaging import version

def download_from_valid_links(link): # supports paste.ee, mclo.gs, and any direct link to a .txt/.log file
    # Check if it's a paste.ee link
    paste_ee_pattern = r'https://paste\.ee/(?:p/|d/)([a-zA-Z0-9]+)'
    paste_ee_match = re.search(paste_ee_pattern, link)
    if paste_ee_match:
        paste_id = paste_ee_match.group(1)
        direct_link = f'https://paste.ee/d/{paste_id}/0'
    else:
        # Check if it's an mclo.gs link
        mclogs_pattern = r'https://mclo\.gs/(\w+)'
        mclogs_match = re.search(mclogs_pattern, link)
        if mclogs_match:
            mclogs_id = mclogs_match.group(1)
            direct_link = f'https://api.mclo.gs/1/raw/{mclogs_id}'
        else:
            # Check if it ends with .txt or .log
            if link.endswith('.txt') or link.endswith('.log'):
                direct_link = link
            else:
                return None
    # Download text from direct link
    response = requests.get(direct_link, timeout=5)
    if response.status_code == 200:
        return response.text.replace('\r', '')


def get_mods_from_log(log):
    # Find all lines that have [✔️] or [✔] before a mod name
    pattern = re.compile(r'\[✔️\]\s+([^\[\]]+\.jar)')
    mods = pattern.findall(log)
    pattern = re.compile(r'\[✔\]\s+([^\[\]]+\n)')
    mods += [mod.rstrip('\n').replace(' ','+')+'.jar' for mod in pattern.findall(log)]
    return mods

def get_mods_type(mods):
    # 0 - no mods, 1 - mods but no fabric mods, 2 - fabric mods but no mcsr mods, 3 - mcsr mods
    mcsr_mods = ['worldpreview','anchiale','sleepbackground','StatsPerWorld','z-buffer-fog',
                'tab-focus','setspawn','SpeedRunIGT','atum','standardsettings','forceport',
                'lazystronghold','antiresourcereload','extra-options','chunkcacher',
                'serverSideRNG','peepopractice','fast-reset']
    fabric_mods = ['Fabric','voyager','fabric']
    if len(mods) == 0:
        return 0
    if any(any(mcsr_mod in mod for mcsr_mod in mcsr_mods) for mod in mods):
        return 3
    if any(any(fabric_mod in mod for fabric_mod in fabric_mods) for mod in mods):
        return 2
    return 1

def get_java_version(log): # returns a string like '19.0.2'
    pattern = re.compile(r'Checking Java version\.\.\.\n(.*)\n')
    match = pattern.search(log)
    if match:
        # Extract the Java version from the next line
        version_line = match.group(1)
        pattern = re.compile(r'Java is version (\S+),')
        version_match = pattern.search(version_line)
        if version_match:
            return version_match.group(1)

def get_major_java_version(java_version):
    if java_version:
        version_parts = java_version.split('.')
        if version_parts[0] != '1':
            return int(version_parts[0])
        return int(version_parts[1])

def get_minecraft_folder(log):
    # Find the line that contains "Minecraft folder is:"
    pattern = re.compile(r'Minecraft folder is:\n(.*)\n')
    match = pattern.search(log)
    if match:
        # Extract the folder location from the next line
        folder_line = match.group(1)
        return folder_line.strip()

def get_os(folder_location,log):
    if folder_location is None:
        if '-natives-windows.jar' in log:
            return 'Windows'
        return None
    if folder_location.startswith('/'):
        if len(folder_location) > 1 and folder_location[1].isupper():
            return 'MacOS'
        return 'Linux'
    return 'Windows'

def get_minecraft_version(log):
    # Find the line that contains "Params:"
    pattern = re.compile(r'Params:\n(.*?)\n', re.DOTALL)
    match = pattern.search(log)
    if match:
        # Extract the version value from the next line
        params_line = match.group(1)
        version_pattern = re.compile(r'--version (\S+)\s')
        version_match = version_pattern.search(params_line)
        if version_match:
            return version_match.group(1)

def extract_fabric_loader_version(log):
    pattern = re.compile(r'Loading Minecraft \S+ with Fabric Loader (\S+)')
    match = pattern.search(log)
    if match:
        return match.group(1)

def get_launcher(log):
    if log[:7] == 'MultiMC':
        return 'MultiMC'
    if log[:5] == 'Prism':
        return 'Prism'
    if log[:6] == 'PolyMC':
        return 'PolyMC'
    if log[:6] == 'ManyMC':
        return 'ManyMC'
    if log[:7] == 'UltimMC':
        return 'UltimMC'

def get_is_multimc_or_fork(launcher):
    return (launcher in ['MultiMC','Prism','PolyMC','ManyMC','UltimMC'])

def get_modloader(log):
    # Find the line that contains "Main Class:"
    pattern = re.compile(r'Main Class:\n(.*)\n')
    match = pattern.search(log)
    if match:
        # Extract the modloader from the next line
        main_class_line = match.group(1)
        if 'quilt' in main_class_line:
            return 'quilt'
        if 'forge' in main_class_line:
            return 'forge'
        if 'fabric' in main_class_line:
            return 'fabric'
        if 'forge' in log.split("\nLibraries:\n", 1)[-1].split("\nNative libraries:\n", 1)[0]:
            return 'forge'
        if 'net.minecraft.client.main.Main' in main_class_line:
            return 'vanilla'

def get_java_arguments(log):
    pattern = re.compile(r'Java Arguments:\n(.*?)\n', re.DOTALL)
    match = pattern.search(log)
    if match:
        arguments_line = match.group(1)
        return arguments_line

def get_max_memory_allocation(log):
    # Find the line that contains "Java Arguments:"
    pattern = re.compile(r'Java Arguments:\n(.*?)\n', re.DOTALL)
    match = pattern.search(log)
    if match:
        # Extract the value after "-Xmx" from the next line
        arguments_line = match.group(1)
        memory_pattern = re.compile(r'-Xmx(\d+)m')
        memory_match = memory_pattern.search(arguments_line)
        if memory_match:
            return int(memory_match.group(1))

def not_using_fabric(modloader,mods_type):
    # 0 - no mods, 1 - mods but no general mods, 2 - general mods but no mcsr mods, 3 - mcsr mods
    if modloader is None or mods_type is None:
        return None
    if modloader == 'forge':
        if mods_type <= 1:
            return "🟡 Note that using Forge isn't allowed for speedrunning."
        if mods_type >= 2:
            return "🔴 You seem to be using Fabric mods, but you have Forge installed. Type `!!fabric` for a guide on how to install fabric."
    elif modloader == 'quilt':
        if mods_type <= 2:
            return "🟡 Note that using Quilt isn't allowed for speedrunning. Type `!!fabric` for a guide on how to install fabric."
        if mods_type == 3:
            return "🔴 You're using Quilt, which is not allowed for speedrunning. Type `!!fabric` for a guide on how to install fabric."
    elif modloader == 'vanilla':
        if mods_type == 3:
            return "🔴 You don't have Fabric installed, while all MCSR mods require it. Type `!!fabric` for a guide on how to install fabric."
        if mods_type == 2:
            return "🔴 The mods you're using require having Fabric installed. Type `!!fabric` for a guide on how to install fabric."
        if mods_type == 1:
            return "🟡 You don't seem to be using a modloader. Type `!!fabric` for a guide on how to install fabric."

def should_use_prism(launcher, operating_system):
    if launcher == 'MultiMC' and operating_system == 'MacOS':
        return '🟡 If you use M1 or M2, it is recommended to use Prism Launcher instead of MultiMC. You can check out this guide for how to set up speedrunning on a Mac: <https://www.youtube.com/watch?v=GomIeW5xdBM>.'

def need_java_17_plus_or_64bit_java(log, mods, major_java_version, mods_type, is_multimc_or_fork):
    needed_java_version = None
    output = ''
    if major_java_version and major_java_version < 17:
        java_17_mods = [mod for mod in mods if
                       'worldpreview-2.' in mod
                       or 'worldpreview-1.0' in mod
                       or 'antiresourcereload' in mod
                       or 'serverSideRNG' in mod
                       or 'setspawnmod' in mod
                       or 'peepopractice' in mod]
        if len(java_17_mods) >= 1:
            needed_java_version = 17
            output += f"🔴 You are using {'mods' if len(java_17_mods)>1 else 'a mod'} (`{'`, `'.join(java_17_mods)}`) that require{'s' if len(java_17_mods)==1 else ''} using Java {needed_java_version}+."
            if any('mcsrranked' in mod for mod in mods):
                update_java = 0
            elif (any('antiresourcereload' in mod for mod in java_17_mods)
            or any('peepopractice' in mod for mod in java_17_mods)
            or any('setspawnmod' in mod for mod in java_17_mods)):
                update_java = 1
            elif (any('worldpreview-2.' in mod for mod in java_17_mods)
            or any('worldpreview-1.0' in mod for mod in java_17_mods)):
                update_java = -1
                output += "Delete it and download the latest version that doesn't require Java 17 from <https://github.com/Minecraft-Java-Edition-Speedrunning/mcsr-worldpreview-1.16.1/releases/latest>."
            else:
                update_java = 0
            if update_java == 1:
                output += '\nUse this guide to update your Java version: <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a>.'
            elif update_java == 0:
                output += f" Delete {'them' if len(java_17_mods)>1 else 'it'} from your `mods` folder."
                if is_multimc_or_fork:
                    output += "\n*(you can use this guide to update your Java version, which is better for performance:* <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a>)"
    if 'Minecraft 1.18 Pre Release 2 and above require the use of Java 17' in log:
        output += "🔴 You are playing on a Minecraft version that requires using Java 17+.\n"
        output += 'Use this guide to update your Java version: <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a>.'
    if output:
        return output
    if 'java.lang.UnsupportedClassVersionError' in log:
        pattern = re.compile(r'class file version (\d+\.\d+)')
        match = pattern.search(log)
        if match:
            needed_java_version = round(float(match.group(1)))-44
    pattern = re.compile(r'The requested compatibility level (JAVA_\d+) could not be set.')
    match = pattern.search(log)
    if match:
        needed_java_version = match.group(1).split('_')[1]
    if needed_java_version:
        return f"🔴 You need to use Java {needed_java_version}+. Use this guide to update your Java version: <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a>."
    if 'Your Java architecture is not matching your system architecture. You might want to install a 64bit Java version.' in log:
        return "🔴 You're using 32-bit Java. See here for help installing the correct version: <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a>."
    if 'Exception in thread "main" java.lang.ClassFormatError: Incompatible magic value 0 in class file sun/security/provider/SunEntries' in log:
        return f"🔴 Your Java installation seems to be broken. Follow this guide to install and select the recommended Java version: <{'https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a' if mods_type == 3 else 'https://prismlauncher.org/wiki/getting-started/installing-java/'}>."

def outdated_srigt_fabric_01415(mods, fabric_loader_version, minecraft_version):
    output = ''
    speedrunigt = [mod for mod in mods if 'SpeedRunIGT' in mod]
    if len(speedrunigt) > 1:
        return '🟡 You have several versions of SpeedRunIGT installed. You should delete the older ones.'
    if len(speedrunigt) == 0:
        return None
    if fabric_loader_version is None:
        return None
    speedrunigt = speedrunigt[0]
    pattern = re.compile(r'-(\d+(?:\.\d+)?)\+')
    match = pattern.search(speedrunigt)
    if match:
        speedrunigt = match.group(1)
        if (version.parse(speedrunigt) < version.parse('13.3')
        and version.parse(fabric_loader_version) > version.parse('0.14.14')):
            output += "🔴 You're using an old version of SpeedRunIGT that is incompatible with Fabric Loader 0.14.15+. You should delete the version of SpeedrunIGT you have and download the latest one from <https://redlime.github.io/SpeedRunIGT/>."
            if minecraft_version != '1.16.1':
                output += '\n*Alternatively, you can use Fabric Loader 0.14.14.*'
    if output:
        return output

def outdated_fabric_loader(fabric_loader_version, mods):
    if fabric_loader_version is None:
        return None
    if version.parse(fabric_loader_version) < version.parse('0.12.2'):
        return "🔴 You're using a really old version of Fabric Loader. You should update it. Type `!!fabric` for instructions on how to do it."
    if version.parse(fabric_loader_version) < version.parse('0.14.0'):
        return f"{'🔴' if any('mcsrranked' in mod for mod in mods) else '🟠'} You're using an old version of Fabric Loader. You should update it. Type `!!fabric` for instructions on how to do it."
    if version.parse(fabric_loader_version) < version.parse('0.14.14'):
        return "🟡 You're using a somewhat old version of Fabric Loader, you might want to update it."
    if fabric_loader_version in ('0.14.15','0.14.16'):
        return "🔴 You're using a completely broken version of Fabric Loader. You should update it. Type `!!fabric` for instructions on how to do it."

def not_enough_ram_or_rong_sodium(max_memory_allocation, operating_system, mods, log, java_arguments, mods_type):
    output = ''
    if max_memory_allocation:
        if (max_memory_allocation < (1200 if ('shenandoah' in java_arguments) else 1900)) and (('OutOfMemoryError' in log) or ('Process crashed with exitcode -805306369' in log)):
            output += '🔴 You have too little RAM allocated. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.y78pfyby3w9b> for a guide on how to fix it.\n'
        elif max_memory_allocation < (850 if ('shenandoah' in java_arguments) else 1200):
            output += '🟠 You likely have too little RAM allocated. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.y78pfyby3w9b> for a guide on how to fix it.\n'
        elif max_memory_allocation < (1200 if ('shenandoah' in java_arguments) else 1800):
            output += '🟡 You likely have too little RAM allocated. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.y78pfyby3w9b> for a guide on how to fix it.\n'
        if max_memory_allocation > 10000 and mods_type == 3:
            output += '🔴 You have way too much RAM allocated, which can cause lag spikes. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.owelqvpsehpw> for a guide on how to fix it.\n'
        elif max_memory_allocation > 4800 and mods_type == 3:
            output += '🟠 You have too much RAM allocated, which can cause lag spikes. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.owelqvpsehpw> for a guide on how to fix it.\n'
        elif max_memory_allocation > 3500 and mods_type == 3:
            output += '🟡 You likely have too much RAM allocated, which can cause lag spikes. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.owelqvpsehpw> for a guide on how to fix it.\n'
    if operating_system == 'MacOS' and (('sodium-1.16.1-v1.jar' in mods) or ('sodium-1.16.1-v2.jar' in mods)):
        output += "🔴 You seem to be using a version of Sodium that has a memory leak on MacOS. Delete the one you have and download <https://github.com/Minecraft-Java-Edition-Speedrunning/mcsr-sodium-mac-1.16.1/releases/tag/latest> instead.\n"
    if output:
        return output.rstrip("\n")
    if 'OutOfMemoryError' in log:
        return '🔴 You likely either have too little RAM allocated, or experienced a memory leak. Check out <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.y78pfyby3w9b> and <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.pmch2xu1p6ce>.'

def onedrive(minecraft_folder,launcher):
    if minecraft_folder and ('OneDrive' in minecraft_folder):
        return f"🟡 Your {launcher if launcher else 'launcher'} folder is located in OneDrive. OneDrive can mess with your game files to save space, and this often leads to crashes. You should move it out to a different folder, and may need to reinstall {launcher if launcher else 'the launcher'}."

def hs_err_pid(log, mods):
    output = ''
    if ('A fatal error has been detected by the Java Runtime Environment' in log
    or 'EXCEPTION_ACCESS_VIOLATION' in log):
        output += '''🟠 This crash may be caused by one of the following:
- Concurrently running programs, such as OBS and Discord, that use the same graphics card as the game.
 - Try using window capture instead of game capture in OBS.
 - Try disabling hardware acceleration in Discord.\n'''
        if any("SpeedRunIGT" in mod for mod in mods):
            output += '- A compatibility issue between SpeedrunIGT, Intel Graphics and OpenGL. Enable “Safe Font Mode” in SpeedrunIGT options. If the game crashes before you can access that menu, delete .minecraft/speedrunigt.\n'
        output += "- Driver issues. Check if your drivers are updated, and update them or downgrade them if they're already updated."
    if output:
        return output.rstrip("\n")

def using_phosphor(mods, minecraft_version):
    if any("phosphor" in mod for mod in mods):
        if any("starlight" in mod for mod in mods):
            return '🔴 Phosphor and Starlight are incompatible. You should delete Phosphor from your mods folder.'
        if minecraft_version != '1.12.2':
            output = "🟡 You're using Phosphor. Starlight is much better than Phosphor, you should use it instead. "
            if minecraft_version == '1.16.1':
                output += "You can download it here: <https://github.com/PaperMC/Starlight/releases/download/1.0.0-RC2/starlight-fabric-1.0.0-RC2-1.16.x.jar>"
            elif minecraft_version == '1.16.5':
                output += "You can download it here: <https://github.com/PaperMC/Starlight/releases/download/1.0.0-RC2/starlight-forge-1.0.0-RC2-1.16.5.jar>"
            elif len(minecraft_version)<4:
                output = "<@695658634436411404> :bug: huh1"
            elif minecraft_version[:4] == '1.15':
                output += "You can download it here: <https://github.com/dariasc/Starlight/releases/tag/1.15%2F1.0.0-alpha>"
            elif float(minecraft_version[:4])>1.16:
                output += "You can download it here: <https://modrinth.com/mod/starlight/versions>"
            else:
                output = "<@695658634436411404> :bug: huh2"
            return output

def failed_to_download_assets(log):
    if 'Instance update failed because: Failed to download the assets index:' in log:
        return '🔴 Try restarting your PC and then launching the instance again.'

def id_range_exceeded(log):
    if 'java.lang.RuntimeException: Invalid id 4096 - maximum id range exceeded.' in log:
        return "🔴 You've exceeded the hardcoded ID Limit. Remove some mods, or install [JustEnoughIDs](<https://www.curseforge.com/minecraft/mc-mods/jeid>)"

def multimc_in_program_files(minecraft_folder,launcher):
    if minecraft_folder and ('C:/Program Files' in minecraft_folder):
        return '🟡 Your {} installation is in `Program Files`. It is generally not recommended, and could cause issues. Consider moving it to a different location.'.format(launcher if launcher else 'launcher')

def macos_too_new_java(log):
    if "Terminating app due to uncaught exception 'NSInternalInconsistencyException', reason: 'NSWindow drag regions should only be invalidated on the Main Thread!'" in log:
        return "🔴 You are using too new of a Java version. Please follow the steps on this wiki page to install 8u241: <https://github.com/MultiMC/MultiMC5/wiki/Java-on-macOS>. You don't need to uninstall the other Java version."

def forge_too_new_java(log):
    if 'java.lang.ClassCastException: class jdk.internal.loader.ClassLoaders$AppClassLoader cannot be cast to class java.net.URLClassLoader' in log:
        return "🔴 You need to use Java **8** to use Forge on this Minecraft version. Use this guide to install it, but make sure to install Java **8** instead of Java 17: <https://docs.google.com/document/d/1aPF1lyBAfPWyeHIH80F8JJw8rvvy6lRm0WJ2xxSrRh8/edit#heading=h.62ygxgaxcs5a>."

def m1_failed_to_find_service_port(log):
    if 'java.lang.IllegalStateException: GLFW error before init: [0x10008]Cocoa: Failed to find service port for display' in log:
        return "🔴 You seem to be using an Apple M1 Mac with an incompatible version of Forge. Add the following to your launch arguments as a workaround: `-Dfml.earlyprogresswindow=false`"

def pixel_format_not_accelerated_win10(log):
    if 'org.lwjgl.LWJGLException: Pixel format not accelerated' in log:
        return "🔴 You seem to be using an Intel GPU that is not supported on Windows 10. You will need to install an older version of Java, see here for help: <https://github.com/MultiMC/MultiMC5/wiki/Unsupported-Intel-GPUs>."

def shadermod_optifine_conflict(log):
    if 'java.lang.RuntimeException: Shaders Mod detected. Please remove it, OptiFine has built-in support for shaders.' in log:
        return "🔴 You've installed a Shaders Mod alongside OptiFine. OptiFine has built-in shader support, so you should remove Shaders Mod."

def using_system_glfw_or_openal(log,launcher):
    using_system_libs = [lib for lib in ['GLFW','OpenAL'] if 'Using system '+lib in log]
    if using_system_libs:
        if any('Failed to locate library: '+lib in log for lib in ['glfw','OpenAL']):
            output = "🔴 You're using your system's "
            if len(using_system_libs) == 2:
                output += "GLFW and OpenAL installations"
            else:
                output += using_system_libs[0] + " installation"
            output += f", which is causing the crash. Disable it either in {launcher if launcher else 'your launcher'}'s global settings in `Settings → Minecraft{' → Tweaks' if launcher == 'Prism' else ''}` or in instance settings in `Settings → Workarounds`."
        else:    
            output = "🟡 You seem to be using your system's "
            if len(using_system_libs) == 2:
                output += "GLFW and OpenAL installations"
            else:
                output += using_system_libs[0] + " installation"
            output += ". This can cause the instance to crash if not properly setup. In case of a crash, make sure this isn't the cause of it."
        return output

def sodium_config(log):
    if 'me.jellysquid.mods.sodium.client' in log:
        return '🔴 If your game crashes when you open the video settings menu or load into a world, delete `.minecraft/config/sodium-options.json`. <@695658634436411404>'

def using_ssrng(mods,is_multimc_or_fork):
    if any(mod == "serverSideRNG-9.0.0.jar" for mod in mods):
        return f"🟡 You are using serverSideRNG. The server for it is currently down, so the mod is useless and it's recommended to {'disable' if is_multimc_or_fork else 'delete'} it."

def random_log_spam_maskers(log):
    if ('Using missing texture, unable to load' in log
    or 'Exception loading blockstate definition' in log
    or 'Unable to load model' in log
    or 'java.lang.NullPointerException: Cannot invoke "com.mojang.authlib.minecraft.MinecraftProfileTexture.getHash()" because "?" is null' in log):
        return "🟢 Your log seems to have lines with random spam. It shouldn't cause any problems, and there aren't any known fixes. <@695658634436411404>"

def need_fapi(log):
    if 'requires any version of fabric, which is missing!' in log:
        return "🔴 You're using a mod that requires Fabric API. It is a mod that is separate to Fabric loader. You can download it here: <https://modrinth.com/mod/fabric-api>."

def dont_need_fapi(mods,mods_type):
    if (mods_type == 3 and any('fabric-api' in mod for mod in mods)
    and not any('mcsrranked' in mod for mod in mods)): # will check for it in a different function
        return "🟠 You're using Fabric API, which is not allowed for speedrunning. Delete it from your `mods` folder."

def couldnt_extract_native_jar(log):
    if "Couldn't extract native jar" in log:
        return '🔴 Another process appears to be locking your native library JARs. To solve this, please reboot your PC.'

def need_to_launch_as_admin(log,launcher):
    # happened in rankedcord: https://discord.com/channels/1056779246728658984/1074385256070791269/1118915678834020372
    pattern = re.compile(r'java\.io\.IOException: Directory \'(.+?)\' could not be created')
    if pattern.search(log):
        return f"🟠 Try opening {launcher if launcher else 'the launcher'} as administrator."

def maskers_crash(log):
    # https://discord.com/channels/928728732376649768/940285426441281546/1107588481556946998 devcord
    if ('java.lang.RuntimeException: We are asking a region for a chunk out of bound' in log
    and 'Encountered an unexpected exception' in log
    and 'net.minecraft.class_148: Feature placement' in log
    and 'net.minecraft.server.MinecraftServer.method_3813(MinecraftServer.java:876)' in log
    and 'at net.minecraft.server.MinecraftServer.method_3748(MinecraftServer.java:813)' in log):
        return "🟢 This seems to be a rare crash that you can't do anything about. So far we only know of one case when it happened. <@695658634436411404>"

def lithium_crash(log):
    # known incidents:
    # https://discord.com/channels/928728732376649768/940285426441281546/1077767432812376265 devcord
    # https://discord.com/channels/928728732376649768/940285426441281546/1093051774409121822 devcord
    # https://discord.com/channels/1056779246728658984/1074302943374872637/1119191694563344434 rankedcord
    if ('java.lang.IllegalStateException: Adding Entity listener a second time' in log
    and 'me.jellysquid.mods.lithium.common.entity.tracker.nearby' in log):
        return "🟢 This seems to be a rare crash caused by Lithium that you can't do anything about. It happens really rarely, so far we only know about 4 times of when it happened to someone, so it's not worth it to not use Lithium because of it."

def old_arr(mods,minecraft_version):
    if ('antiresourcereload-1.16.1-1.0.0.jar' in mods) and (minecraft_version == '1.16.1'):
        return "🔴 You're using an old version of AntiResourceReload, which can cause Minecraft to crash when entering practice maps. You should update it: <https://github.com/Minecraft-Java-Edition-Speedrunning/mcsr-antiresourcereload-1.16.1/releases/tag/latest>"

def limited_graphics_capability(log):
    # happened in javacord:
    # https://discord.com/channels/83066801105145856/727673359860760627/1119184648896000010
    if 'GLFW error 65543: WGL: OpenGL profile requested but WGL_ARB_create_context_profile is unavailable' in log:
        return """🔴 Your issue stems from using Intel HD2000 integrated graphics, which only supports up to OpenGL 3.1. Unfortunately, there are no dedicated Windows 10 drivers available for this graphics card. As a result, you will not be easily able to run Minecraft 1.17+, as 21w10a and later require improved graphics capabilities beyond OpenGL 3.1. You should still be able to play Minecraft versions 1.16 and earlier.
For more information about this issue and possible solutions, please refer to the following link: <https://prismlauncher.org/wiki/getting-started/installing-java/#a-note-about-intel-hd-20003000-on-windows-10>"""

def exitcode_1073741819(log):
    if ('Process crashed with exitcode -1073741819 (0xffffffffc0000005).' in log
    or 'The instruction at 0x%p referenced memory at 0x%p. The memory could not be %s.' in log):
        return '''🔴 Your game crashed with exitcode `-1073741819`. Here are some possible solutions:
- Check if you have a controller plugged in. If you do, unplug it.
- Reboot your pc.
- Some mods may cause this crash for currently unknown reasons. So far, this has happened with Sodium, SleepBackground, and LazyDFU. Try removing these mods/other mods one by one and testing if the game still crashes.
- Make sure you have the latest graphics driver.'''

def exitcode_805306369_or_old_ssrng(log,mods):
    pattern = r'^serverSideRNG-[1-8]\.0\.0\.jar$'
    if any(re.match(pattern, mod) for mod in mods):
        return "🔴 You're using an old version of serverSideRNG, which is now illegal and can often cause problems. The server for it is currently down, so the mod is useless regardless and you should delete it."
    if ('Process crashed with exitcode -805306369' in log
    or 'java.lang.ArithmeticException: / by zero' in log
    or ('########## GL ERROR ##########' in log and '@ Render' in log)):
        return "🟠 Check your options.txt file for any values that are set to 0 and are not supposed to be 0 (such as `maxFps:0`). If you find any, change them to the values you want and save the file."

def ranked_non_whitelisted_mods(mods,log,is_multimc_or_fork):
    if not any('mcsrranked' in mod for mod in mods):
        return None
    output = ''
    whitelisted_mods = ['sodium','replaymod','extra-options','retino','worldpreview',
                        'sleepbackground','SpeedRunIGT','atum','standardsettings',
                        'forceport','lazystronghold','antiresourcereload','serverSideRNG',
                        'BiomeThreadLocalFix','mcsrranked','fast-reset','starlight',
                        'phosphor','lithium','krypton','dynamic-menu-fps','lazydfu',
                        'voyager','forceport','FabricProxy-Lite']
    non_whitelisted_mods = [mod for mod in mods if not any(w_mod in mod for w_mod in whitelisted_mods)]
    if non_whitelisted_mods:
        pattern = r'The Fabric Mod "(.*?)" is not whitelisted!'
        matches = re.findall(pattern, log)
        if matches: # if ranked complains about non-whitelisted mods
            # non_whitelisted_mods_and_libs = list(matches)
            if any('fabric-api' in mod for mod in non_whitelisted_mods):
                output += "🔴 You're using Fabric API. It is a mod separate to Fabric Loader, and it isn't allowed for speedrunning. Delete it from your `mods` folder.\n"
            practice_mods = ['peepopractice','stronghold-trainer','noverworld','blinded',
                             'heatshrink','lavapool-juicer','cageless','no-spawnchunks',
                             'treasure-juicer','no-basalt','shipwreck-juicer','logmod']
            practice_mods = [nw_mod for nw_mod in non_whitelisted_mods if any(p_mod in nw_mod for p_mod in practice_mods)]
            if len(non_whitelisted_mods) != len(practice_mods):
                output += f"🔴 You are using {'mods' if len(non_whitelisted_mods)>1 else 'a mod'} ({', '.join(non_whitelisted_mods)}) that {'is' if len(non_whitelisted_mods)==1 else 'are'}n't whitelisted for MCSR Ranked. Delete {'it' if len(non_whitelisted_mods)==1 else 'them'} from your `mods` folder.\n"
            else:
                output += f"🔴 You are using {'practice mods' if len(practice_mods)>1 else 'a practice mod'} ({', '.join(practice_mods)}) that {'is' if len(practice_mods)==1 else 'are'}n't allowed to be used when playing Ranked."
                if is_multimc_or_fork:
                    output += f" You should either create a separate practice instance for {'them' if len(practice_mods)>1 else 'it'} or disable {'them' if len(practice_mods)>1 else 'it'}."
                output += "\n"
        else: # if ranked doesn't complain about non-whitelisted mods
            output = f"<@695658634436411404> :bug: {'are' if len(non_whitelisted_mods)>1 else 'is'} ({', '.join(non_whitelisted_mods)}) whitelisted?\n"
        if output:
            return output
        return "<@695658634436411404> :bug: huh3"

def using_autoreset_instead_of_atum(mods,log):
    if ('autoreset-1.2.0+MC1.16.1.jar' in mods
    or 'java.lang.RuntimeException: Non-unique Mixin config name autoreset.mixins.json used by the mods atum and autoreset' in log):
        return "🔴 You're using AutoReset. It's a really old mod that is no longer allowed, and Atum is a better version of it. You can download Atum here: <https://modrinth.com/mod/atum/versions>."

def need_to_update_ranked(mods):
    if 'mcsrranked-1.2.2.jar' in mods:
        return "🔴 You're using an old version of the MCSR Ranked mod, which no longer works. You should delete it from your mods folder and download the latest one from <https://modrinth.com/mod/mcsr-ranked/versions/>."

def need_to_launch_online(log):
    if 'Failed to find Minecraft main class:' in log:
        return "🔴 You need to launch your instance online at least once for the launcher to download assets."

def javacheck_jar_on_prism(log,minecraft_version,modloader,operating_system):
    pattern = r'This instance is not compatible with Java version (\d+)\.\nPlease switch to one of the following Java versions for this instance:\nJava version (\d+)'
    match = re.search(pattern, log)
    if match:
        switch_java = 0.5
        if modloader == 'forge':
            switch_java = 1
        elif minecraft_version and minecraft_version[:4] in ['1.18','1.19','1.20','1.21','1.22','1.23']:
            switch_java = 1
        elif minecraft_version and minecraft_version[:4] == '1.16': # prob 1.16.1 mcsr mods/1.16.5 setspawn
            switch_java = 0
        current_version = int(match.group(1))
        compatible_version = int(match.group(2))
        if switch_java == 1:
            return f"🔴 You're using Java {current_version}, while you need to use Java {compatible_version} for this instance. You can download Java {compatible_version} from <https://adoptium.net/temurin/releases/>{' (download the .msi file)' if operating_system == 'Windows' else ' (download the .pkg file)' if operating_system == 'MacOS' else ''}. Then make sure to select Java {compatible_version} either globally or in instance settings."
        if switch_java == 0:
            return "🔴 Disable the Java compatibility check in `Settings > Java` either in instance settings or in global settings."
        return f"🔴 Either use Java {compatible_version} for this instance or disable the Java compatibility check in `Settings > Java` either in instance settings or in global settings."
    return None

def class_not_found_error(log):
    # happened in mmccord: https://discord.com/channels/132965178051526656/134843027553255425/1120073012906049639
    if 'Caused by: java.lang.ClassNotFoundException: org.apache.logging.log4j.spi.AbstractLogger' in log:
        return "🔴 Try deleting the folder `.../MultiMC/libraries/org/apache/logging/log4j` and then launching the instance again."

def random_forge_crashes(log):
    # happens on 1.20.1 with forge 47.0.14 for me on prism
    if 'java.lang.RuntimeException: Unable to detect the forge installer!' in log:
        return "🔴 Try launching your instance online if you aren't. Also, try using a different version of Forge."
    # happened in prismcord: https://discord.com/channels/1031648380885147709/1098659300651577425
    if 'java.lang.NoClassDefFoundError: cpw/mods/modlauncher/Launcher' in log:
        return "🔴 Try restarting the launcher, creating an instance without Forge and then installing Forge on this instance."


def parse_log(link):
    log = download_from_valid_links(link)
    if log is None:
        return None
    mods = get_mods_from_log(log)
    mods_type = get_mods_type(mods)
    java_version = get_java_version(log)
    major_java_version = get_major_java_version(java_version)
    minecraft_folder = get_minecraft_folder(log)
    operating_system = get_os(minecraft_folder,log)
    minecraft_version = get_minecraft_version(log)
    fabric_loader_version = extract_fabric_loader_version(log)
    launcher = get_launcher(log)
    is_multimc_or_fork = get_is_multimc_or_fork(launcher)
    modloader = get_modloader(log)
    java_arguments = get_java_arguments(log)
    max_memory_allocation = get_max_memory_allocation(log)
    issues = [
        not_using_fabric(modloader,mods_type),
        should_use_prism(launcher,operating_system),
        need_java_17_plus_or_64bit_java(log,mods,major_java_version,mods_type,is_multimc_or_fork),
        outdated_srigt_fabric_01415(mods,fabric_loader_version,minecraft_version),
        outdated_fabric_loader(fabric_loader_version,mods),
        not_enough_ram_or_rong_sodium(max_memory_allocation, operating_system, mods, log, java_arguments, mods_type),
        onedrive(minecraft_folder,launcher),
        hs_err_pid(log,mods),
        using_phosphor(mods,minecraft_version),
        failed_to_download_assets(log),
        id_range_exceeded(log),
        multimc_in_program_files(minecraft_folder,launcher),
        macos_too_new_java(log),
        forge_too_new_java(log),
        m1_failed_to_find_service_port(log),
        pixel_format_not_accelerated_win10(log),
        shadermod_optifine_conflict(log),
        using_system_glfw_or_openal(log,launcher),
        sodium_config(log),
        using_ssrng(mods,is_multimc_or_fork),
        random_log_spam_maskers(log),
        need_fapi(log),
        dont_need_fapi(mods,mods_type),
        couldnt_extract_native_jar(log),
        need_to_launch_as_admin(log,launcher),
        maskers_crash(log),
        lithium_crash(log),
        old_arr(mods,minecraft_version),
        limited_graphics_capability(log),
        exitcode_1073741819(log),
        exitcode_805306369_or_old_ssrng(log,mods),
        ranked_non_whitelisted_mods(mods,log,is_multimc_or_fork),
        using_autoreset_instead_of_atum(mods,log),
        need_to_update_ranked(mods),
        need_to_launch_online(log),
        javacheck_jar_on_prism(log,minecraft_version,modloader,operating_system),
        class_not_found_error(log),
        random_forge_crashes(log)
    ]
    result = []
    for issue in issues:
        if issue:
            result.append(issue)
    return result
