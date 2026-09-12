# PDF Splitter
This is a simple script to split a *PDF* file into multiple files, according to page ranges provided by the user.

## The Problem

There are some excellent free websites to split *PDF* files. However, these have some common limitations:
* Data protection concerns inherent in uploading the document to a connected server.
* File size limitations imposed by most such websites.   
* Full preview of the *PDF* document, allowing the user to determine the page ranges on the fly.

## Usage

### Running the script

When you run the *Python* script, it will pop up a file explorer/finder window asking you to select the source *PDF* file.

You should type in the page range(s) in the "*Enter page ranges*" field. You may input multiple ranges separated by commas, e.g., *1-2,3-4*. For single page ranges, just input the page number, e.g., *1*.

A preview of the document is provided that you can browse to determine the correct page numbers, if needed.

If you would like the selected page ranges to be combined into a single PDF, select the "*Combine all ranges into one file*" option.

### Output

The script will save the output as *PDF* files in the same folder as the original.

### Note

1. The script uses some standard *Python* libraries. If you don't have them installed on your system, then in the first run, the script will try to install these dependencies. If the script can't install these dependencies, for instance if your PC environment precludes it, then it will usually give you the console commands you can use to install these.
2. If some of your libraries and executables sit outside the *Path*, such as if you don't have Admin rights to your work laptop, then you should include the folder addresses in the '*path.txt*' file, which should sit in the same folder as the '*pdf-splitter.py*' file, e.g. '*C:\Users\Username\AppData\Roaming\Python\Python313\Scripts*' and '*C:\Users\Username\AppData\Roaming\Python\Python313\site-packages*'.

## Caveat

Tested on *Windows 11 Education 64-bit*.

Not tested on *Apple iOS* or *Linux*.

## Never run a Python script before?

It's straightforward, but you may need to install *Python* on your machine first.

### Install Python

*Anaconda* is one of the most popular distributions of *Python*. Download and install from https://www.anaconda.com/download

Installation is simple, but if you need help, check out https://www.anaconda.com/docs/getting-started/anaconda/install/overview

### Start Spyder

*Anaconda* comes with *Spyder IDE*. Start *Spyder*.

Once *Spyder* is ready, open the file '*pdf-splitter.py*' that has the script.

All that's left is for you to hit 'Run', i.e. the green 'Play' button.