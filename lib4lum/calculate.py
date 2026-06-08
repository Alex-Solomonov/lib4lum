from .dependencies import *

def run_folder(folder_path) -> None:
    """
    """
    
    clean_path = folder_path / 'clean'
    solved_path = folder_path / 'solved'

    names = clean_path.glob('*.fsp')
    for file in names:
        ### Dummy way to load correct type
        ###ToDo later
        ###ToDo kwards hide option
        savename = solved_path / file.name
        client = lumapi.FDTD(str(file), hide = True)

        # client.run()

        client.save(str(savename))
        client.close()
        os.remove(file)


def run_project(project_path) -> None:
    """
    """

    folder_list = [x for x in project_path.iterdir() if x.is_dir()]

    for folder in tqdm(folder_list):
        run_folder(folder)