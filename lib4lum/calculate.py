from .dependencies import *
from multiprocessing import Pool
from psutil import cpu_count

def _default_processes() -> int:
    """
    half the logical CPU cores,
    the FDTD memory-bandwidth limit
    """
    return max(1, (cpu_count(logical=False) or 2) // 2)

def _run(file : Path | str, cores : int = 2, **kwards):
    '''
    cores : int
        Logical cores (physical + thread according documentation)
    '''
    savename = file.parent.parent / 'solved' / file.name
    ### Dummy way to load correct type
    client = lumapi.FDTD(str(file), processes = cores, **kwards)

    client.run()

    client.save(str(savename))
    client.close()
    os.remove(file)

def run_folder(folder_path : Path | str, **kwards) -> None:
    '''
    Run all FDTD simulation files located in the 'clean' subdirectory,
    save the solved projects to the 'solved' subdirectory, and remove
    the original files after successful completion.
    The function searches for all '.fsp' files in
    'folder_path / 'clean', opens each project using the Lumerical
    FDTD API, executes the simulation, saves the solved project to
    'folder_path / 'solved', closes the session, and deletes the
    original project file.

    Args:
        folder_path: Path | str
            Root directory containing the 'clean' and 'solved'
            subdirectories.

    Returns:
        None
    '''

    if 'multiprocessing' in kwards:
        workers = _default_processes()
        child_cores = 1
    else:
        workers = 1
        child_cores = _default_processes()

    clean_path = folder_path / 'clean'

    names = clean_path.glob('*.fsp')
    with Pool(processes = workers) as pool:
        pool.map(_run, names, child_cores)
      
def run_project(project_path : Path | str, **kwards) -> None:
    '''
    Process all simulation folders within a project directory.
    The function iterates through all subdirectories of 'project_path'
    
    Args:
        folder_path: Path | str
            Root directory containing the 'clean' and 'solved'
            subdirectories.

    Returns:
        None
    '''

    folder_list = [x for x in project_path.iterdir() if x.is_dir()]

    for folder in tqdm(folder_list):
        run_folder(folder, **kwards)