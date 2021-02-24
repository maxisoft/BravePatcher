# Brave Patcher
<img src="https://raw.githubusercontent.com/brave/brave-browser/master/docs/source/_static/product_logo_32.png" style="filter: invert(100%);"/>

![Brave Analysis](https://github.com/maxisoft/BravePatcher/workflows/Brave%20Analysis/badge.svg) ![CI](https://github.com/maxisoft/BravePatcher/workflows/CI/badge.svg)

## Patcher capabilities
- Earn BAT faster
- Hide Ads notifications
- Disable browser updates

## Limitations
- **Only x64 windows** version of brave is currently supported
- Needs of re-patching Brave every update
- May not work in the future

## How to use
### on windows:
- [Download](https://github.com/maxisoft/BravePatcher/releases/download/v0.1.0/BravePatcher_gui.exe) and start the latest release (gui.exe)
- Optional: *tick* or *un-tick* patching options
- Click `Patch`
- Recommended: Disable browser update in `Tool -> Brave Update -> Disable`

## Download
Heads over the [Release page](https://github.com/maxisoft/BravePatcher/releases/tag/v0.1.0)

## Screenshot
![](https://img.tedomum.net/data/gui-61dd21.jpeg)

## Design
This project is a proof of concept for working with tools such GHidra and various recent python libs.
My main goal is to test and use GHidra as replacement of IDA disassembly tool in a rather simple project.


## FAQ
### Brave is suddenly crashing when I start it
In case you have an error [like this](https://www.reddit.com/r/brave_browser/comments/kwdz4w/the_browser_completely_crashes_whenever_i_try_to/),
you have to reinstall brave using **official** installer and re-patch.  
To prevent this error one need to disable the brave update.

## Technical FAQ
### Why not just simply edit brave source and build a patched version ?
- It may be more flexible and straightforward but it's not my first [goal](#design)
- Building brave require building chrome.dll which is one of the biggest monolithic shared library out there. AFAIK there's no free CI offering enough resources to successfully built brave.
- In attempt to prevent building such a patched brave, Brave devs would move the client side BAT source code away from github
### Thought about GHidra
GHidra is a powerful tool and on top of that it's free and opensource :)  
Performance wise it seems pretty good. Not as fast as IDA on analysis time but kinda the same order of magnitude.  
The scripting - for automatic binary pre-post processing such as pattern extraction- part seems Java focused (too much imo) with a good amount of examples.
Scripting non trivial pre/post processing logics is an experience with a bit of javadoc reading and trials and errors which is somehow time-consuming (pettry common in the Reverse Engineering field).