import curses
import time
import random
import argparse
import math
import csv
from collections import defaultdict

# Read the list of words and choose N of them

streaks  = defaultdict(int)
selected = defaultdict(bool)
weights  = defaultdict(int)
words = []
with open("./words.txt", "rb") as f:
  for row in csv.reader(f, delimiter='\t'):
    if len(row) > 0:
      selected[row[0]] = False
      words.append(row[0])
      if len(row) > 1:
        streaks[row[0]] += int(row[1])
      weights[row[0]] = 100 / max(streaks[row[0]] + 1, 100)


def draw_word(window, y, word, color, reversed=False):
  color = curses.color_pair(color) | curses.A_BOLD
  if reversed:
    color = color | curses.A_REVERSE

  if "$" in word:
    next_color    = color
    current_color = curses.color_pair(8) | curses.A_BOLD

    current_x = 6
    for chunk in word.split("$"):
      chunk_length = len(chunk)
      if chunk_length > 0:
        window.addstr(y, current_x, chunk, current_color)
        current_x += chunk_length
      current_color, next_color = next_color, current_color

  else: # just a normal word
    window.addstr(
      y,
      6,
      word,
      color)

  window.clrtoeol()
  window.refresh()

def draw_toolbar(toolbar, vals):
  color = curses.color_pair(8)
  toolbar.addstr(
    0,
    0,
    "{}:{}:{}:{}".format(*vals),
    color)
  toolbar.clrtoeol()
  toolbar.refresh()

def main_application(stdscr, word_count, is_testing):

  # choose word_count words from the word list as our operating list
  word_count = min(word_count, len(words))

  new_words = set()

  random.shuffle(words) # not sure if this matters

  # grab a weigted random sample where smaller streaks are favored
  total_weight = sum(weights.values())
  for _ in range(word_count):
    random_choice = random.randint(1, total_weight)
    word_iter = iter(sorted(weights.items(), key=lambda x: x[1]))
    cword = ""
    while random_choice > 0:
      (cword, cweight) = word_iter.next()
      random_choice -= cweight
    selected[cword] = True
    new_words.add(cword)
    del(weights[cword])
    total_weight -= cweight





  # create default buckets
  wordlist = []
  wordlist.append(new_words)
  wordlist.append(set()) # missed
  wordlist.append(set()) # working
  wordlist.append(set()) # mastered

  current_list = 0 # start on the new bucket
  # start with the new word list as the working list
  working_list = list(wordlist[current_list])
  random.shuffle(working_list)

  all_mastered = False
  aborted = False

  # set up the windows
  win_dim = stdscr.getmaxyx()
  stdscr.nodelay(1)
  curses.curs_set(0)

  toolbar = stdscr.subwin(1, win_dim[1], win_dim[0] - 1, 0)
  mainwin = stdscr.subwin(win_dim[0] - 1, win_dim[1], 0, 0)

  mainwin_middle = mainwin.getmaxyx()[0] / 2


  # set up the colors
  curses.start_color()
  curses.use_default_colors()
  for i in range(0, curses.COLORS):
    curses.init_pair(i, i, -1);

  # COLORS
  # curses.color_pair(1) -- RED
  # curses.color_pair(2) -- GREEN
  # curses.color_pair(3) -- YELLOW
  # curses.color_pair(4) -- BLUE
  # curses.color_pair(5) -- PURPLE
  # curses.color_pair(6) -- aqua
  # curses.color_pair(7) -- white
  # curses.color_pair(8) -- gray

  # associate word colors with buckets
  word_colors = {
    0 : 4,
    1 : 1,
    2 : 3
  }

  # colors for the timer bullets
  bullet_colors = {
    0 : 8,
    1 : 7,
    2 : 2,
    3 : 3,
    4 : 1
  }


  while not all_mastered:


    current_word = working_list.pop()
    mainwin.erase()

    finished   = False
    time_start = time.time()
    time_diff  = -1
    draw_word(
      mainwin,
      mainwin_middle,
      current_word,
      word_colors[current_list])

    draw_toolbar(toolbar, [len(x) for x in wordlist])
    out_of_time = False


    while not finished:
      time_diff_temp = int(math.floor((time.time() - time_start)))

      if (time_diff_temp is not time_diff):
        # new second
        time_diff = time_diff_temp
        if time_diff < 10 and time_diff % 2 == 0:
          # add tickers
          mainwin.addstr(
            mainwin_middle,
            time_diff / 2,
            ":",
            curses.color_pair(bullet_colors[time_diff / 2]) | curses.A_BOLD)
          mainwin.refresh()
        elif time_diff == 10:
          out_of_time = True
          draw_word(
            mainwin,
            mainwin_middle,
            current_word,
            word_colors[current_list],
            True)

      inputkey = stdscr.getch()
      if inputkey == ord('q'):
        all_mastered = True
        finished     = True
        aborted      = True
      elif inputkey in [ord("1"), ord("2"), ord("3")]:
        wordlist[current_list].remove(current_word)
        finished     = True
        if inputkey == ord("1"): # missed always go to missed
          wordlist[1].add(current_word)
          streaks[current_word] = 0 # reset score
        elif current_list == 1: # missed cards can only go to a working at best
          wordlist[2].add(current_word)
        else: # working cards can go up to mastered
          if inputkey == ord("2") or out_of_time:
            wordlist[2].add(current_word) # back to working
          else:
            wordlist[3].add(current_word) # up to mastered
            streaks[current_word] = streaks[current_word] + 1 # increase score


    #####
    # check if the current list is empty, and if so jump to the next
    # if the next is mastered, then end.
    if len(working_list) == 0:
      next_list = next(
        (idx for idx, val in enumerate(wordlist) if len(val) > 0))

      # if the only list with words is mastered, we're done
      if (next_list == 3):
        all_mastered = True
      else:
        current_list = next_list
        working_list = list(wordlist[current_list])
        random.shuffle(working_list)

  ### WRITE WORDS.TXT BACK WITH UPDATED STREAKS

  if not is_testing:
    with open("words.txt", "wb") as f:
      writer = csv.writer(f, delimiter='\t')
      for key in sorted(
        streaks.keys(),
        key=lambda x: (streaks[x] * -1, x.lower())):
        writer.writerow([key, streaks[key]])

  ### DISPLAY VICTORY SCREEN

  if not aborted:

    praise = [
      "AWESOME",
      "GREAT JOB",
      "SUPER",
      "EXCELLENT",
      "FANTASTIC",
      "FABULOUS",
      "WOW",
      "AMAZING",
      "WONDERFUL"
    ]

    praise_string = "VICTORY! YOU WON! :-) {}!".format(random.choice(praise))
    mainwin.erase()
    draw_word(mainwin, mainwin_middle, praise_string, 2)
    draw_toolbar(toolbar, [len(x) for x in wordlist])

    stdscr.nodelay(0) # wait for key input
    stdscr.getch()






def bootstrap(word_count, testing):
  curses.wrapper(main_application, word_count, testing)




if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Test some vocabulary words.')
  parser.add_argument(
    "word_count",
    metavar="n",
    type=int,
    help="Number of words to test")
  parser.add_argument('--test', action='store_true')

  args = parser.parse_args()

  bootstrap(args.word_count, args.test)
