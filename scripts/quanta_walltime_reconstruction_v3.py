"""V2 exact-prefix guards plus narrowly scoped ctypes library-discovery processes."""
from pathlib import Path
from quanta_walltime_reconstruction_v2 import identity,task_key,select_identity,checked_cache_bytes,assert_recorded_request,assert_boundary_counts

def permit_library_process(args,*,shell=False,executable=None,stdlib_verified=False,function=None,library=None,temporary_output=None,soname_file=None):
    if not isinstance(args,(list,tuple)) or not args or shell or executable not in [None,args[0]]:return False
    if list(args)==['/sbin/ldconfig','-p']:return True
    if not stdlib_verified or library!='blosc2':return False
    if function=='_findLib_gcc':
        return len(args)==5 and Path(args[0]).name in ['gcc','cc'] and list(args[1:3])==['-Wl,-t','-o'] and args[3]==temporary_output and args[4]=='-lblosc2'
    if function=='_findLib_ld':
        middle=list(args[2:-3])
        return list(args[:2])==['ld','-t'] and list(args[-3:])==['-o','/dev/null','-lblosc2'] and len(middle)%2==0 and all(middle[i]=='-L' and isinstance(middle[i+1],str) for i in range(0,len(middle),2))
    if function=='_get_soname':
        return len(args)==5 and Path(args[0]).name=='objdump' and list(args[1:4])==['-p','-j','.dynamic'] and args[4]==soname_file and 'libblosc2' in str(soname_file)
    return False
