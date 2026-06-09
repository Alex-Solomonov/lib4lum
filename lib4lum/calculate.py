from .dependencies import *

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
    clean_path = folder_path / 'clean'
    solved_path = folder_path / 'solved'

    names = clean_path.glob('*.fsp')
    for file in names:
        ### Dummy way to load correct type
        ###ToDo later
        ###ToDo kwards hide option
        savename = solved_path / file.name
        client = lumapi.FDTD(str(file), **kwards)

        client.run()

        client.save(str(savename))
        client.close()
        os.remove(file)


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