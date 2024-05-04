"""Update WSL2 kernel if outdated using release info from github."""

import configparser
import json
import os
import requests
import subprocess
from functools import cmp_to_key

# TODO: Use logging library

force_update = False
kernel_file_name = 'bzImage-x64v3'
releases_url = (
  'https://api.github.com/repos/Locietta/xanmod-kernel-WSL2/releases'
)

config_path = '/mnt/c/Users/Joshua Wierenga/.wslconfig'
download_path = '/mnt/c/Users/Joshua Wierenga/wsl'

# Restrictions
# Only enable lts and X/Y restriction not both
only_lts = True
only_x = 0  # 0 means any, must be set if only_y is set
only_y = 0  # 0 means any


# TODO: Support downloading more than one page
# Currently this makes the X.Y restrictions less useful
def download_github_kernel_release_info() -> list[dict] | None:
    """Download kernel release info from github."""
    response = requests.get(releases_url)

    if response.status_code != 200:
        print('Error: Unable to download list of recent kernel releases')
        return None

    return json.loads(response.content)


def get_newest_github_kernel_release_info(release_info: list[dict]) \
  -> dict | None:
    """Find newest release, possibly with a filter applied."""
    if only_lts:
        filtered_release_info = [
          release for release in release_info if 'lts' in release['name']
        ]
    elif only_x != 0 and only_y != 0:
        filtered_release_info = [
          release for release in release_info
          if release['name'].startswith(f'{only_x}.{only_y}')
        ]
    elif only_x != 0:
        filtered_release_info = [
          release for release in release_info
          if release['name'].startswith(str(only_x))
        ]
    else:
        filtered_release_info = release_info

    sorted_release_info = sorted(filtered_release_info,
      key=cmp_to_key(lambda r1, r2: compare_kernel_releases(
        split_kernel_release(r1['name']), split_kernel_release(r2['name'])
      ))
    )

    if len(sorted_release_info) == 0:
        if only_lts:
            print('Error: Unable to find any LTS releases')
        elif only_x != 0 and only_y != 0:
            print(f'Error: Unable to find any {only_x}.{only_y}.Z releases')
        elif only_x != 0:
            print(f'Error: Unable to find any {only_x}.Y.Z releases')
        else:
            print('Error: Unable to find any releases')
        return None

    return sorted_release_info[-1]


def get_github_kernel_download_url(release_info: dict) -> str | None:
    """Find url for specified kernel name annd version."""
    for asset in release_info['assets']:
        if asset['name'] != kernel_file_name:
            continue

        return asset['browser_download_url']

    print(f'Error: No kernel image called {kernel_file_name} could be found')
    return None


def download_github_kernel(url: str, name: str) -> str | None:
    """Download chosen kernel from github if not already downloaded."""
    output_path = f'{download_path}/{name}'

    if os.path.isfile(output_path):
        print('Error: New kernel already exists, not overriding')
        return None

    response = requests.get(url)

    if response.status_code != 200:
        print('Error: Unable to download kernel from github')
        return None

    with open(output_path, 'xb') as f:
        f.write(response.content)

    return output_path


def get_current_kernel_path() -> str | None:
    """Get the path to the currently installed WSL2 kernel."""
    if not os.path.isfile(config_path):
        print('Error: Unable to find wslconfig')
        return None

    config = configparser.ConfigParser()
    config.read(config_path)

    if not config.has_section('wsl2'):
        print('Error: wslconfig is missing required wsl2 section')
        return None

    if not config.has_option('wsl2', 'kernel'):
        print('Error: wslconfig is missing required kernel option')
        return None

    return config['wsl2']['kernel']


# Expecting X.Y.Z-locietta-WSL2-xanmodU.V(-lts)
# Returns (X, Y, Z, U, V)
def split_kernel_release(release: str) -> tuple[int] | None:
    """Compare two github kernel releases and return -1, 0, 1 accordingly."""
    name_sections = release.split('-')
    if (len(name_sections) < 4 or not name_sections[3].startswith('xanmod')
         or name_sections[3] == 'xanmod'):
        return None

    version_sections = name_sections[0].split('.')
    if len(version_sections) != 3:
        return 0

    version_x = int(version_sections[0])
    version_y = int(version_sections[1])
    version_z = int(version_sections[2])

    patch_number = name_sections[3].split('xanmod', 1)[1]
    patch_number_sections = patch_number.split('.')
    if len(patch_number_sections) != 2:
        return 0

    patch_u = int(patch_number_sections[0])
    patch_v = int(patch_number_sections[1])

    return (version_x, version_y, version_z, patch_u, patch_v)


# Expecting (X, Y, Z, U, V)
def compare_kernel_releases(release_1: tuple[int], release_2: tuple[int]) \
  -> int:
    """Compare two kernel releases and return -1, 0, 1 accordingly."""
    if len(release_1) != 5 or len(release_2) != 5:
        return 0

    # X.Y.Z checks
    # 2.Y.Z > 1.Y.Z
    if release_1[0] > release_2[0]:
        return 1
    # 1.Y.Z < 2.Y.Z
    elif release_1[0] < release_2[0]:
        return -1
    # 1.1.Z > 1.0.Z
    elif release_1[1] > release_2[1]:
        return 1
    # 1.0.Z < 1.1.Z
    elif release_1[1] < release_2[1]:
        return -1
    # 1.0.1 > 1.0.0
    elif release_1[2] > release_2[2]:
        return 1
    # 1.0.0 < 1.0.1
    elif release_1[2] < release_2[2]:
        return -1

    # U.V checks
    # 2.V > 1.V
    elif release_1[3] > release_2[3]:
        return 1
    # 1.V < 2.V
    elif release_1[3] < release_2[3]:
        return -1
    # 1.1 > 1.0
    elif release_1[4] > release_2[4]:
        return 1
    # 1.0 < 1.1
    elif release_1[4] < release_2[4]:
        return -1

    return 0


def convert_wsl_path(path: str) -> str:
    """Use wslpath to convert a unix path to a windows path."""
    result = subprocess.check_output(
        ['wslpath', '-w', path]
    )
    return result.decode('utf-8')


def update_wslconfig(current_kernel_path: str, new_kernel_path: str) -> bool:
    """Update wslconfig to use mention new kernel."""
    if not os.path.isfile(config_path):
        print('Error: Unable to find wslconfig')
        return None

    with open(config_path, 'r') as f:
        lines = f.read()

    index = lines.find(f'\nkernel={current_kernel_path}\n')
    if index == -1:
        print('Error: wslconfig is missing required kernel option')
        return False

    preped_new_path = new_kernel_path[:-1].replace('\\', '\\\\')

    new_lines = (
      lines[:index] + f'\nkernel={preped_new_path}\n# ' + lines[index + 1:]
    )

    with open(config_path, 'w') as f:
        f.write(new_lines)

    return True


if __name__ == '__main__':
    print('Downloading kernel version info')

    releases = download_github_kernel_release_info()
    if releases is None:
        exit(1)

    newest_kernel_info = get_newest_github_kernel_release_info(releases)
    if newest_kernel_info is None:
        exit(1)

    newest_kernel_name = newest_kernel_info['name']
    newest_kernel_version = split_kernel_release(newest_kernel_name)
    if newest_kernel_version is None:
        exit(1)

    current_kernel_path = get_current_kernel_path()
    if current_kernel_path is None:
        exit(1)

    current_kernel_name = current_kernel_path.split('\\')[-1]
    current_kernel_version = split_kernel_release(current_kernel_name)
    if current_kernel_version is None:
        exit(1)

    print(f'Current version: {current_kernel_name}')
    print(f'Newest version:  {newest_kernel_name}')

    if (
      not force_update and
      compare_kernel_releases(newest_kernel_version, current_kernel_version)
      != 1
    ):
        print('Kernel already up to date and force_update not enabled')
        exit(0)

    print('Updating kernel')

    kernel_download_url = get_github_kernel_download_url(newest_kernel_info)
    if kernel_download_url is None:
        exit(1)

    print(f'Downloading kernel from {kernel_download_url}')

    new_kernel_path = download_github_kernel(
      kernel_download_url, newest_kernel_name
    )
    if new_kernel_path is None:
        exit(1)

    print(f'Downloaded kernel to {new_kernel_path}')
    print('Updating wsl config to use new kernel')

    new_win_kernel_path = convert_wsl_path(new_kernel_path)
    update_wslconfig(current_kernel_path, new_win_kernel_path)

    print('Done, restart wsl to use the new kernel')
