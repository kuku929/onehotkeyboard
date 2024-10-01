###################################################################
#
# @Author: Krutarth Patel
# @Date: 30th October 2024
# @Description: A Real-time keyboard heatmap generator
#               NOTE: this has been tested on Linux and Windows
#               The provided settings work well on both but 
#               for better visuals consider changing the following
#               parameters:
#               - mesh_granularity: 1000 will give a finer heatmap,
#                                   current is 100
#
###################################################################
import string
import argparse
import xml.etree.ElementTree as ET
from enum import Enum
from xml.etree.ElementTree import Element

import matplotlib.colors as colors
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

class Tags(str, Enum):
    """
    @brief: common tags used in the xml file
    """
    Row = "row"
    Key = "key"
    Position = "pos"
    Keyboard = "kbd"
    X = "x"
    Y = "y"


def get_keys(node: Element):
    """
    @brief: convenience function for getting 
    key child from given node
    """
    if node.tag != Tags.Row:
        raise ValueError(
            f"get_keys should be called with node.tag = {Tags.Row}, node is ", node.tag
        )
    return node.iter(Tags.Key)


def get_rows(node: Element):
    """
    @brief: convenience function for getting 
    row child from given node
    """
    if node.tag != Tags.Keyboard:
        raise ValueError(
            f"get_rows should be called with node.tag = {Tags.Keyboard}, node is ",
            node.tag,
        )
    return node.iter(Tags.Row)


def get_positions(node: Element):
    """
    @brief: convenience function for getting 
    pos child from given node
    """
    if node.tag != Tags.Key:
        raise ValueError(
            f"get_positions should be called with node.tag = {Tags.Key}, node is ",
            node.tag,
        )
    position = node.findall(Tags.Position)
    if position is None:
        raise ValueError(f"no position specified for {node.get('char')}")
    if len(position) > 1:
        print(
            f"multiple positions given for {node.get('char')}, dropping all except first"
        )
    return position[0]


def get_x(node: Element):
    """
    @brief: convenience function for getting 
    x child from given node
    """
    if node.tag != Tags.Position:
        raise ValueError(
            f"get_x should be called with node.tag = {Tags.Position}, node is ",
            node.tag,
        )
    elem = node.find(Tags.X)
    if elem is None:
        raise ValueError("x coordinate for a key is not specified")
    return float(elem.text)


def get_y(node: Element):
    """
    @brief: convenience function for getting 
    y child from given node
    """
    if node.tag != Tags.Position:
        raise ValueError(
            f"get_x should be called with node.tag = {Tags.Position}, node is ",
            node.tag,
        )
    elem = node.find(Tags.Y)
    if elem is None:
        raise ValueError("y coordinate for a key is not specified")
    return float(elem.text)


def find_nested_key(nested_dict, key):
    """
    @brief: finds the given key in a nested dictionary.
    @params: nested_dict should be of the form
    {row: {nested-dict}, row2: {another-nested-dict}}
    """
    for dict in nested_dict.values():
        try:
            val = dict[key]
            return val
        except:
            continue
    return


class xmlParser:
    """
    @brief: xml parser for KBF( keyboard file format (
    parses the given file and generates a tree for effecient
    retrieval of data.
    """
    def __init__(self, filename: string):
        try:
            self.tree = ET.parse(filename)
            self.root = self.tree.getroot()
            self.special_keys = [
                "shift_l",
                "shift_r",
                "space",
                "backspace",
                "tab",
                "capslock",
                "enter",
            ]
            self.__reset_count()
            # home row keys
            self.home_row = {}
            # what about shift+key? we can keep a dictionary of lower:upper,
            self.shift_mapping = {}

            # stores the default shift mappings in the qwerty layout
            # will default to this if the shifted key is not provided
            # in the xml file
            self.__default_shift()

            # parse the file and create a dictionary of dictionaries
            # holding the whole keymap.
            # example: {row1: {key1:pos1, key2:pos2,...}, row2:...}
            self.__generate_keymap()
        except Exception as e:  
            raise ValueError("failed to parse!", e)
            

    def __generate_keymap(self):
        """
        @brief: generates the keymap as a nested dictionary
        """
        self.keymap = {}
        self.__reset_count()
        for row in get_rows(self.root):
            row_map = {}
            for key in get_keys(row):
                lower_key = self.__generate_keylist(key)
                position = get_positions(key)
                row_map[lower_key] = (get_x(position), get_y(position))
            row_id = row.get("id")
            if(row_id.lower()=="home"):
                self.home_row.update(row_map)
            # one may specify a row at different places in the file
            # this will handle that
            if row_id in self.keymap.keys():
                self.keymap[row.get("id")].update(row_map)
            else:
                self.keymap[row.get("id")] = row_map
        if not self.home_row:
            raise ValueError("Please specify the home row for your layout by setting the row tag as 'home'")
        self.is_generated = True

    def __reset_count(self):
        """
        @brief: resets the char_count dictionary
        the char_count array is required to check 
        for multiple definitions of keys
        """
        self.char_count = {char: 0 for char in list(string.printable)}
        for key in self.special_keys:
            self.char_count[key] = 0

        self.is_generated = False

    def print_keymap(self):
        """
        @brief: prints the keymap 
        """
        # if you have generated the keymap already
        # reset and do it again
        self.__reset_count()

        for row in get_rows(self.root):
            print(row.get("id"))
            for key in get_keys(row):
                lower_key = self.__generate_keylist(key)
                position = get_positions(key)
                print(lower_key, get_x(position), get_y(position))
        self.is_generated = True

    def __default_shift(self):
        self.default_shift_mapping = {
            char: char.upper() for char in string.ascii_lowercase
        }
        # number row
        self.default_shift_mapping["`"] = "~"
        self.default_shift_mapping["1"] = "!"
        self.default_shift_mapping["2"] = "@"
        self.default_shift_mapping["3"] = "#"
        self.default_shift_mapping["4"] = "$"
        self.default_shift_mapping["5"] = "%"
        self.default_shift_mapping["6"] = "^"
        self.default_shift_mapping["7"] = "&"
        self.default_shift_mapping["8"] = "*"
        self.default_shift_mapping["9"] = "("
        self.default_shift_mapping["0"] = ")"
        self.default_shift_mapping["-"] = "_"
        self.default_shift_mapping["="] = "+"

        # right side
        self.default_shift_mapping["["] = "{"
        self.default_shift_mapping["]"] = "}"
        self.default_shift_mapping["\\"] = "|"  # escape seq
        self.default_shift_mapping[";"] = ":"
        self.default_shift_mapping["'"] = '"'
        self.default_shift_mapping[","] = "<"
        self.default_shift_mapping["."] = ">"
        self.default_shift_mapping["/"] = "?"

        # the special keys are mapped to themselves by default
        for special_key in self.special_keys:
            self.default_shift_mapping[special_key] = special_key

    def show_root(self):
        """
        show the root node
        """
        print(self.root.tag, self.root.attrib)

    def show_children(self, node: Element):
        """
        show the direct children of the node
        """
        for child in node:
            print(child.tag, child.attrib)

    def __generate_keylist(self, node: Element):
        """
        @brief: given a key tag, it checks for the 
        validity of the lower and upper charecter 
        and the position provided
        since we keep a count of characters 
        to check for multiple definitions
        this function should be called only if
        the count array is 0. i.e. __reset_count() should
        be called after/before calling this function
        """
        if self.is_generated:
            print("__generate_keylist function can only be called once")
            return

        if node.tag != "key":
            raise ValueError("node should have a key tag")
        
        keylist = []
        # look for the lower key, this needs to be specified
        lower_char = node.get("lower")
        if lower_char is None:
            raise ValueError(f"Attribute 'lower' for node {node.tag} not found, You need to specify it")
            
        keylist.append(lower_char)
        
        # look for an upper key, if it is specified add to the
        # keylist. Else we use the default shift mapping in the 
        # qwerty layout
        upper_char = node.get("upper")
        if upper_char is not None: 
            keylist.append(upper_char)

        # checking if the charecters are allowed characters
        char = keylist[0]
        if char.lower() not in self.char_count.keys():
            raise ValueError("Invalid key charecter ", char, node.find('pos')[0].text)
        if self.char_count[char.lower()] > 1:
            raise ValueError(
                f"The key {char} is defined more than once, it can only be defined once"
            )

        # lowering so that user can provide 'Space' or 'sPace'
        # and the program won't complain.
        self.char_count[char.lower()] += 1

        if len(keylist) == 2:
            # the second charecter is the shifted version of the first
            if "shift" in keylist[0].lower():
                raise ValueError("shift itself cannot have a shifted mapping")
            if keylist[0] in self.special_keys:
                # if its a special key, we lower it
                self.shift_mapping[keylist[0].lower()] = keylist[1]
            else:
                self.shift_mapping[keylist[0]] = keylist[1]
        # if only one value is provided, map shifted version to the qwerty default
        else:
            # if char is an uppercase alphabet, throw an error since we donot
            # have a default shift mapping
            if char in string.ascii_uppercase:
                raise KeyError(
                    f"default value for {keylist[0]} not found, make sure it is one of these: {self.default_shift_mapping.keys()}"
                ) from None
            try:
                # lowering so that user can provide 'Space' or 'sPace'
                self.shift_mapping[keylist[0].lower()] = self.default_shift_mapping[
                    keylist[0].lower()
                ]
                return char.lower()
            except KeyError:
                raise KeyError(
                    f"default value for {keylist[0]} not found, make sure it is one of these: {self.default_shift_mapping.keys()}"
                ) from None

        # return the lower charecter
        return char


class Painter:
    def __init__(self, keymap: dict, shift_mapping: dict, home_row: dict):
        self.keymap = keymap
        self.home_row = home_row
        self.shift_mapping = shift_mapping
        # we adjust the keys to align them properly
        # saving the adjusted coordinates in this dictionary
        self.visual_keymap = {}

        # since we are doing a density based 
        # heatmap, we store the points 
        # in these two lists
        self.heatmap_pointsx = []
        self.heatmap_pointsy = []

        self.special_keys = {}
        self.special_keys[" "] = "space"
        self.special_keys["\t"] = "tab"
        self.special_keys["/r"] = "enter"
        self.special_keys["\x7f"] = "backspace"
        
        # the default size of one key
        self.xsize = 1.0
        self.ysize = 1.0

        # offset for printing the key charecter
        self.xoffset = -self.xsize / 4
        self.yoffset = -self.ysize / 4

        # needed for drawing the 
        # bounding box for pcolormesh
        self.xmax = 0.0
        self.ymax = 0.0 

        # we get a handle to these axes
        # and redraw each time we get a new charecter
        self.fig, self.ax = plt.subplots()
        self.fig.set_size_inches(15,5)
        # the colormap to use for the heatmap
        self.cmap = plt.colormaps["YlGnBu"]
        self.cmap = plt.colormaps["seismic"]
        self.cmap = plt.colormaps["hot"]
        self.cmap = plt.colormaps["cool"]
        self.cmap = plt.colormaps["coolwarm"]
        
        # drawing the keyboard
        # since the keys are static in our
        # case, we can save them for effecient
        # animations, lookup 'blitting'
        # in matplotlib for more details
        self.__draw_keys(self.keymap, self.shift_mapping)
        self.cbar = self.fig.colorbar(ax=self.ax, cmap=self.cmap, mappable=None)
        
        # we show the plot and capture the image
        # for faster rendering
        plt.show(block=False)
        plt.pause(1)
        
        # load the saved background
        self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        
        # initializing the heatmap mesh
        # this will be animated and drawn on top
        # of the static image 

    	# NOTE: decrease this value if
    	# the heatmap is rendered slowly 
    	# on your machine. A value of 
    	# 100 is ideal but on windows
    	# it lags a bit on my machine at least
        mesh_granularity = 1000
        self.xi, self.yi = np.mgrid[
            -1 : self.xmax : (self.xmax * mesh_granularity)**0.5 * 1j, -1 : self.ymax : (self.ymax * mesh_granularity)**0.5 * 1j
        ]
        
        # the intensity at the start is assumed to be zero
        # hard coding the expected bounds of the heatmap
        # we will clip all values greater than this bound
        bounds = np.linspace(0, 0.07, 10)
        norm = colors.BoundaryNorm(boundaries=bounds, ncolors=256,clip=True)
        self.zi = np.zeros(self.xi.shape)
        self.im = self.ax.pcolormesh(
            self.xi, self.yi, self.zi, alpha= 0.7, cmap=self.cmap, zorder=1,
            norm= norm,
            animated=True
        )
        
        # animated artists need to be called to draw
        self.__draw_artists()
        # update the figure with heatmap
        self.fig.canvas.blit(self.fig.bbox)
        
    def close(self):
        print("Saving image to heatmap.png...")
        plt.savefig('heatmap.png')
        plt.close()

    def __update_points(self, pos):
        """
        at the position pos, we add points
        with a radial spread.
        resulting in more density near pos
        and gradually decreasing farther away
        """
        points = 1 # the no of points
        distance = 0.1 # radius
        delta = 2  # radius*=delta
        while distance < 1:
            points =  points*3 # reduce density
            for point in range(points):
                angle = 2 * np.pi * point / points
                x = pos[0] + distance * np.cos(angle)
                y = pos[1] + distance * np.sin(angle)
                self.heatmap_pointsx.append(x)
                self.heatmap_pointsy.append(y)
            distance *= delta

    def update_heatmap(self, chars):
        """
        @brief: this will be called every tick
        when stdin is updated
        clear the axes and redraw the keyboard
        """
        dist_travelled = 0.0
        for char in chars:
            if char in self.special_keys.keys():
                # space, shift_l etc. keys need to be
                # accounted for separately
                # since the stdin will give \n for enter
                # \b for backspace etc.
                char = self.special_keys[char]

            pos = find_nested_key(self.visual_keymap, char)
            if pos is None:
                # if char not found
                # checking for shifted charecters
                # position of the shift charecter used
                for lower, upper in self.shift_mapping.items():
                    if upper == char:
                        pos = find_nested_key(self.visual_keymap, lower)
                        if pos is not None:
                            self.__update_points(
                                (pos[0] + self.xsize / 2, pos[1] + self.ysize / 2)
                            )
                            shift_char = 'shift_r' if pos[0] < self.xmax/2 else 'shift_l'
                            shift_pos = find_nested_key(self.visual_keymap, shift_char) 
                            # adding heat to shift key as well
                            self.__update_points((shift_pos[0] + self.xsize / 2, shift_pos[1] + self.ysize / 2))
                            break
                        else:
                            print(f"{upper} not found", flush=True)
            else:
                self.__update_points((pos[0] + self.xsize / 2, pos[1] + self.ysize / 2))
            dist_travelled += min([((pos[0]-home[0])**2 + (pos[1]-home[1])**2)**0.5 for home in self.home_row.values()])
            
        # once all the points in the heatmap are updated, draw it
        x = np.array(self.heatmap_pointsx)
        y = np.array(self.heatmap_pointsy)
        
        # we drop points once the size of the array
        # gets larger that maxsize
        # a larger value means the heatmap is more
        # gradual in change thus capturing more keypresses
        # while smaller size means the heatmap changes
        # fast and looks really cool 
        maxsize = 3000
        if maxsize < x.size:
            x = np.delete(x, np.s_[0 : x.size - maxsize])
            y = np.delete(y, np.s_[0 : y.size - maxsize])
            
        # produces a gaussian distribution 
        # based on the density of the points
        k = gaussian_kde(np.vstack([x, y]))
        
        # sampling over a range
        zi = k(np.vstack([self.xi.flatten(), self.yi.flatten()]))
        
        # restore the saved background
        self.fig.canvas.restore_region(self.bg) 
        # update the heatmap
        self.im.set_array(zi.reshape(self.xi.shape))
        # draw again 
        self.__draw_artists()
        self.fig.canvas.blit(self.fig.bbox)
       
        # make sure everything is shown 
        self.fig.canvas.flush_events()
        
        return dist_travelled

    def __draw_artists(self):
        self.ax.draw_artist(self.im)
        
    def __draw_keys(self, keymap: dict, shift_mapping: dict):
        """
        @brief: draws the keyboard layout
        """
        xdata = []
        ydata = []
        
        xsize = self.xsize
        ysize = self.ysize
        xoffset = self.xoffset
        yoffset = self.yoffset
        # padding for gap between two keys
        padding = 0.3
        
        ordered_keymap = {}
        for row in keymap.values():
            for char in row.keys():
                x = row[char][0]
                y = row[char][1]
                if y in ordered_keymap.keys():
                    ordered_keymap[y].append((char, x))
                else: ordered_keymap[y] = [(char, x)]
        
        plt.gca().invert_yaxis()  # if origin is on top left corner
        
        for y, lst in ordered_keymap.items():
            # the second field is x coordinate
            sort_by_x = (lambda tup1: tup1[1])
            # arranging keys from left to right
            lst.sort(key=sort_by_x)
            
            # adjusting keys so that the boxes
            # do not intersect, previous x coordinate
            # is needed for that purpose
            prev_x = lst[0][1]
            self.visual_keymap[y] = {}
            count = 0
            for char, x in lst:
                xdata.append(max(x, prev_x + xsize + padding))
                ydata.append(y)
                # some parameters to draw boxes 
                # around charecters and such
                xsize = self.xsize
                ysize = self.ysize
                xoffset = self.xoffset
                yoffset = self.yoffset
                # padding for gap between two keys
                padding = 0.3

                # the first and the last keys are usually
                # bigger
                if count ==0:
                    xsize+=1.5
                if count == len(lst)-1:
                    xsize+=1.2

                # saving the adjusted values
                self.visual_keymap[y][char] = (xdata[-1], ydata[-1])
                if xdata[-1]+xsize+padding > self.xmax:
                    self.xmax = xdata[-1]+xsize+padding
                if ydata[-1]+ysize > self.ymax:
                    self.ymax = ydata[-1]+ysize+padding
                
                # darkorange for home row keys
                ec = "g"
                if char in self.home_row.keys():
                   ec="darkorange" 
                # adding bounding box
                self.ax.add_patch(
                    patches.FancyBboxPatch(
                        (xdata[-1], ydata[-1]), xsize, ysize-padding, edgecolor=ec, facecolor="none", zorder=1,
                        boxstyle="Round, pad=0.1" 
                    )
                )
                # charecter text
                self.ax.text(xdata[-1] + xsize / 2, y + ysize / 2, char, zorder=1)
                self.ax.text(
                    xdata[-1] + xsize / 2 + xoffset,
                    y + ysize / 2 + yoffset,
                    shift_mapping[char.lower()],
                    zorder=1
                )
                prev_x = xdata[-1]
                count+=1
        # drawing top left points
        # for some reason the canvas is not drawn
        # if this is not here
        plt.scatter(xdata, ydata)

class AsyncIO:
    """
    This class takes in charecters from the 
    standard input without waiting for an 
    EOL charecter. The implementation is 
    different for windows and linux
    """
    def set(self):
        # this is unix specific
        import sys, termios, tty
        # courtesy of https://code.activestate.com/recipes/134892/
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        try:
            tty.setraw(sys.stdin.fileno())
        except Exception as err:
            print("initializing of asyncio failed ", err)
    def getch(self, charecter_stream: string):
        try:
            # if linux
            return self.getch_unix(charecter_stream)
        except ImportError:
            # else windows
            return self.getch_win(charecter_stream)
            
    def getch_win(self, charecter_stream: string):
        # this is windows specific
        import msvcrt
        charecter_stream += msvcrt.getch().decode('ASCII')
        return charecter_stream
            
    def getch_unix(self, charecter_stream: string):
        # this is unix specific
        import sys, termios, tty
        self.set()
        charecter_stream += sys.stdin.read(1)
        if "\r" in charecter_stream:
            raise KeyboardInterrupt()
        self.reset()
        return charecter_stream

    def reset(self):
        try:
            import sys, termios, tty
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
        except ImportError:
            return



def main():
    print("""
                    ***  Welcome to no mistaeks Typing!  ***
                    *  If your machine allows, you will    *
		    *    see a keyboard window which       *
                    *  updates in real time as you type    *
                    *  Also,the backspace doesnt work:)    *
	  	    ****************************************

preparing a keyboard for you...""")
    cmdparser = argparse.ArgumentParser(
        prog='onehotkeyboard',
        description='keyboard heatmap generator',
    )
    cmdparser.add_argument('filename')
    args = cmdparser.parse_args()
    parser = xmlParser(args.filename)
    painter = Painter(parser.keymap, parser.shift_mapping, parser.home_row)
    asyncio = AsyncIO()
    print("Start Typing, press Enter to stop...")
    
    distance_travelled = 0.0
    charecter_stream = ""
    try:
        while True:
            # main event loop
            charecter_stream = asyncio.getch(charecter_stream)
            if "\r" in charecter_stream:
                raise KeyboardInterrupt()
            print(charecter_stream[-1], flush=True , end="")
            distance_travelled += painter.update_heatmap(charecter_stream)
            # drop charecters after updated
            # since we have no use for them
            charecter_stream = ""
    except KeyboardInterrupt:
        asyncio.reset()
        print("\nYour fingers travelled a total distance of: ", distance_travelled)
        painter.close()
        print("Shutting down...")
    except Exception as err:
        asyncio.reset()
        print("giving up...did you press backspace?", err)

if __name__ == "__main__":
    main()
