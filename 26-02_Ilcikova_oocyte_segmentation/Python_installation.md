# Editor
Visual Studio Code is the editor I use, but it is also possible to edit the script from another text editor, such as Notepad
VS Code installation: [https://code.visualstudio.com/](https://code.visualstudio.com/ "https://code.visualstudio.com/")

VS Code requires additional Python extension to be able to run Python code - this is not necessary if the script is run directly from the terminal
Guide on installing extensions: [https://code.visualstudio.com/docs/configure/extensions/extension-marketplace](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace "https://code.visualstudio.com/docs/configure/extensions/extension-marketplace")

# Python and package manager installation
To be able to manage different Python installations and libraries, we use conda. Conda can be used from Miniforge Prompt (or alternatively also Miniconda or Anaconda), installable from this link: [https://conda-forge.org/download/](https://conda-forge.org/download/ "https://conda-forge.org/download/")

After installing Miniforge Prompt, we also need to install the actual environment, that will contain Python, as well as other necessary Python libraries. 
This installation can be done by pasting the following commands one after another to the Miniforge Prompt: 
1. Create the environment itself (in this case named 'general') and fill it with installation of Python 3.13 (some other versions should also be ok).
```
conda create -n general python=3.13 -y
```
2. Activate the environment so that libraries can be added to it: 
```
conda activate general
```
3. Install libraries needed for bioimage analysis: 
```
pip install numpy pandas matplotlib scikit-image openpyxl
```

**Alternatively**, the environment can be installed from the attached [yml file](generalCondaEnv.yml) using the following command (*path* has to be changed to where the yml file is located):
```
conda env create -f C:/path/generalCondaEnv.yml
```
