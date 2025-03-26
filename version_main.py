docs_version = "0.1.0"
package_version = "0.1.2"


def update_lines(file_path, start_with, replacement_string):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    with open(file_path, "w") as f:
        for line in lines:
            if line.strip().startswith(start_with):
                print(f'replacing {line}\nwith {replacement_string}')
                f.write(f'{replacement_string}\n')
            else:
                f.write(line)

def update_docs():
    update_lines('./docs/docs/index.md', 'pyPicoSDK:', f'pyPicoSDK: {package_version}')
    update_lines('./docs/docs/index.md', 'Docs:', f'Docs: {docs_version}')

def update_setup():
    update_lines('./setup.py', 'version=', (' '*4) + f'version="{package_version}",')

def update_src():
    update_lines('./picosdk/version.py', 'VERSION', f'VERSION = "{package_version}"')

def update_versions():
    update_docs()
    update_setup()
    update_src()

if __name__ == "__main__":
    update_versions()