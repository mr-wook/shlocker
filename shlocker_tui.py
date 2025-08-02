#!/bin/env python3.13
"""shlocker is a docker container management tool;"""

if True:
    import docker
    from   functools import partial
    import json
    import os
    import logging # from   logger import logger
    from   pathlib import Path
    import pdb
    import platformdirs
    from   pprint import pprint, pformat
    import re
    from   rich import print as rprint
    from   rich.console import Console
    import subprocess
    import sys
    import time

    # sys.path.insert(1, ".")
    from tui3 import Tui3


class ServerClient:
    SERVER = "http://localhost:6502"

    def __init__(self):
        pass

if __name__ == "__main__":
    class App:
        LOGFILE = "/var/log/shlocker/shlocker.log"
        REXHEX = re.compile(r'[0-9a-fA-F]+')
        def __init__(self):
            self._console = Console()
            self.data_home = platformdirs.user_data_dir("shlocker", "mr.wook@gmail.com")
            self._width = self._get_width() - 1
            self._logger_setup()
            self._ui = Tui3(prompt="shlocker> ")
            self._set_dispatch()
            self._docker = docker.from_env()
            self.reload()
            self._persistence = self.load()
            return

        def clean(self, ui, *args):
            # 'all' means all non-running containers;
            # 'junk' means all non-running containers with no name;
            junk = all_ = False
            if not args:
                junk = True
                all_ = False
            elif 'all' in args:
                all_ = True
            elif 'junk' in args:
                junk = True
            images = self._docker.images.list(all=True)
            untagged = [img for img in images if not img.tags]
            untagged_ids = [img.short_id[7:] for img in untagged]
            running_ids = [xc.short_id for xc in self._docker.containers.list(all=True) if xc.status == 'running']
            stopped = [xc for xc in self._docker.containers.list(all=True) if xc.status == 'stopped']
            non_running_images = [xi for xi in images if xi.short_id[7:] not in running_ids] # Remember RepoTags;
            target_images = non_running_images
            removals = self._docker.containers.prune()
            pprint(removals)
            return True
            for xt in target_images:
                xt_attrs = xt.attrs
                rt = xt_attrs['RepoTags'] if xt_attrs['RepoTags'] else ""
                # breakpoint()
                name = xt.tags[0] if xt.tags else "<none>"
                if name != "<none>":
                    continue
                print(f"{name} {xt.short_id[7:]} {rt}")
                xt.remove()
            return True

        def _columnize(self, list_):
            max_col_width = max([len(item) for item in list_]) + 1
            n_cols = (self._width // max_col_width) - 1
            ostr = ""
            n_items = 0
            for item in list_:
                ostr = f"{ostr} {str(item):<{max_col_width}}"
                n_items += 1
                if n_items % n_cols == 0:
                    ostr += "\n"
            return ostr

        def _container_info(self, *args):
            c_info = [fn for fn in dir(self._by_state['running'][0]) if not fn.startswith('_')]
            c_info.sort()
            print(self._columnize(c_info)) # Replace this with a simple instance?
            return True

        def echo(self, ui, *args):
            print(" ".join([str(arg) for arg in args]))
            return True

        def forget(self, ui, *args):
            containers = self._persistence
            if not containers:
                print(f"No persistent containers")
                return False
            all_containers = self._all_containers
            if args == ( None, ):   # No args artifact, forget all; -- if not ui.args?
                self._persistence = [ ]
                self.save()
                self._info("All containers unpersisted")
                return True
            else:
                forgotten = 0
                for c_spec in args:
                    cont = self._match(c_spec)
                    if not cont:
                        print(f"No container matched spec {c_spec}")
                        continue
                    c_id = cont.id
                    if not c_id in self._persistence:
                        continue
                    print(f"Forgetting {cont.id} ({cont.id})")
                    del self._persistence[c_id]
                    forgotten += 1
            # pprint(self._persistence)
            if forgotten:
                self._info(f"{forgotten} containers forgotten")
                self.save()
            return True

        def _get_width(self):
            subp = subprocess.Popen(['tput', 'cols'], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            so, se = subp.communicate()
            rc = subp.wait()
            so = so.decode().strip()
            if so.isdigit():
                width = int(so)
            else:
                width = 100
            return width

        def _gray(self, txt, rc=True):
            self._print(f"[gray]{txt}")
            return rc

        def help(self, ui, *args):
            cmdnames = list(ui.cmdnames)
            specials = [cmd for cmd in cmdnames if cmd.startswith('%')]
            cmds = [cmd for cmd in cmdnames if not cmd.startswith('%')]
            cmds.sort()
            specials.sort()
            print(self._columnize(specials))
            print(self._columnize(cmds))
            return True

        def _info(self, txt, rc=True):
            self._print(f"[blue][{txt}]")
            return rc

        def info(self, ui, *args):
            which = args[0]
            print(f"which: {which}")
            containers = self._docker.containers.list(all=True)
            if self._is_hex(which):
                for c in containers:
                    if c.id.endswith(which):
                        print(self._info_long(c))
                return True
            else:
                for c in containers:
                    if c.name == which:
                        print(self._info_long(c))
                return True
            return False

        def _info_long(self, c):
            labels = ' '.join([f"{k}: {c.labels[k]}" for k in c.labels])
            ostr = f"{c.name} {c.id} {c.status} {labels}" + '\n'
            ostr = f"{ostr}{c.top}"
            return ostr
 
        def _is_hex(self, s: str):
            if s is None:
                return False
            return App.REXHEX.match(s)

        def load(self, *args) -> dict:
            "Load from default storage if exists, else return Null dict"
            ifn = f"{self.data_home}/shlocker.json"
            if args == ( None, ): # Load from default name
                pass
            elif len(args) < 2:
                pass
            else:
                ifn = args[1]
            if not os.path.isfile(ifn):
                return dict()
            with open(ifn, 'r') as ifd:
                ibuf = ifd.read(8 * 1024)
            return json.loads(ibuf)

        def _logger_setup(self):
            log_file = App.LOGFILE
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            logging.basicConfig(filename=log_file, filemode='a',  # append mode
                                format='%(asctime)s [%(levelname)s] %(message)s',
                                level=logging.INFO)  # or DEBUG, WARNING, etc.
            # logging.info("Shlock logger initialized.")

        def ls(self, ui, *args):
            self.reload()
            colors = dict(running='green', exited='red')
            which = [ 'running' ]
            if '--all' in args:
                which = list(self._by_state.keys())
            for state in which:
                if not self._by_state[state]:
                    continue
                self._print(state.upper(), style="bold")
                color = "default"
                if state in colors:
                    color = colors[state]
                for xc in self._by_state[state]:
                    view = self._view(xc)
                    if xc.id in self._persistence:
                        self._print(f"[{color}] * {view}")
                    else:
                        self._print(f"[{color}]{view}")
            return True

        def _match(self, id_or_name, which_containers = 'running'):
            match which_containers:
                case 'all':
                    containers = self._all_containers
                case None:
                    containers = self._all_containers
                case _:
                    containers = self._by_state[which_containers]

            if self._is_hex(id_or_name):
                c_matches = [c for c in containers if c.id.endswith(id_or_name)]
                if not c_matches:
                    print(f"Nothing matched id: {id_or_name}")
                    return False
                if len(c_matches) > 1:
                    print(f"Ambiguous {id_or_name}")
                    return False
                return c_matches[0]

            c_matches =  [c for c in containers if c.name == id_or_name]
            if not c_matches:
                return False
            if not len(c_matches):
                print(f"Nothing matched name {id_or_name}")
                return False
            if len(c_matches) > 1:
                print(f"Too many matches for {id_or_name}")
                return False
            return c_matches[0]

        def pdb(self, *args):
            breakpoint()
            return True

        def persist(self, ui, *args):
            containers = self._by_state['running']
            if not containers:
                print(f"No running containers, nothing to persist")
                self._review_persistent()
                return False
            if args == ( None, ):   # No args artifact;
                # breakpoint()
                for c in containers:
                    if c.id not in self._persistence:
                        self._persistence[c.id] = True
                        continue
                    self._persistence[c.id] = True
            else:
                for which in args:
                    print(f"Persisting {which}")
                    c = self._match(which)
                    if not c:
                        print(f"Can't find container matching {c}")
                        continue
                    self._persistence[c.id] = True
            pprint(self._persistence)
            self.save()
            return True

        def _print(self, *args, **kwa):
            self._console.print(*args, **kwa)

        def pstat(self, ui, *args):
            if args == ( None, ):
                cmd = [ "docker", "ps" ]
            else:
                cmd = [ "docker", "ps"] + list(args)
            print(f"{' '.join(cmd)}")
            subp = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            so, se = subp.communicate()
            rc = subp.wait()
            print(f"{so.decode().strip()}")
            if se:
                print(f"Errors: {se.decode}")
                print(f"rc={rc}")
            return True

        def _port_mappings(self, c):
            portmappings = c.attrs['NetworkSettings']['Ports']
            ostr = ""
            for port in portmappings:
                ostr = f"{ostr}{port}:"
                v4, v6 = portmappings[port]
                v4src = "*" if v4['HostIp'] == "0.0.0.0" else v4['HostIp']
                v4src = f"{v4src}/{v4['HostPort']}"
                v6src = "*" if v6['HostIp'] == "::" else v6['HostIp']
                v6src = f"{v6src}/::{v6['HostPort']}"
                ostr = f"{ostr}{v4src}, {v6src} "
            return ostr

        def _mount_bind_mappings(self, c):
            volumes = dict([(e['Source'], e['Destination']) for e in c.attrs['Mounts'] if e['Type'] == 'bind'])
            vnames = list(volumes.keys())
            vnames.sort()
            ostr = ""
            for vol in vnames:
                ostr = f"{ostr}{vol}:{volumes[vol]} "
            return ostr

        def quitter(self, ui, *args):
            sys.exit(0)

        def _red(self, txt, rc=True):
            self._print(f"[red]{txt}")
            return rc

        def reload(self, *args):
            "Get status for all containers, and group by state;"
            self._all_containers = all_ = self._docker.containers.list(all=True)
            states = list(set([c.status for c in all_]))
            self._by_state = dict(running=[], exited=[])  # Sleazy hack;
            for state in states:
                self._by_state[state] = [c for c in all_ if c.status == state]
            return True

        def restart(self, ui, *args):
            return self.start_stop("restart", *ui.args)

        def restore(self, *args, **kwa):
            if not self._persistence:
                self._red("Nothing persistent to restore")
            _all_containers = self._all_containers
            _all_container_ids = [c.id for c in _all_containers]
            restored = 0
            for pc_id in self._persistence:
                if pc_id not in _all_container_ids:
                    self._red("No container {pc_id} available to restore")
                    continue
                cont = [rcont for rcont in _all_containers if pc_id == rcont.id][0]
                cont.start()
                restored += 1
                self._print(f"[blue]{self._view(cont)}")
            self._info(f"{restored} containers restarted")
            return restored

        def _review_persistent(self):
            _all_containers = self._all_containers
            _all_container_ids = [c.id for c in _all_containers]
            for pc_id in self._persistence:
                if pc_id not in _all_container_ids:
                    self._console.print("[gray]{pc_id} not found")
                    continue
                c = [c for c in _all_containers if c.id == pc_id][0]
                print(self._view(c))
            return

        def rm(self, ui, *args):
            if not ui.args:
                print(f"No container specified for removal")
                return False
            self.reload()
            c = self._match(ui.args[0], 'all')
            if not c:
                print(f"No such container")
                return False
            if c.status == 'running':
                print(f"Won't stop running container {c.name}")
                return False
            print(f"Removing {c.name} ({c.id})")
            rc = c.remove()
            return True

        def run(self):
            self._ui.mainloop()
            return True

        def running_p(self, c):
            return c in self._by_state['running']

        def save(self, *args):
            "Save persistent state;"
            # Consider changing content to { key: { persist: t/f, restart: t/f, rebuild: f, name: c.name }}
            ofn = f"{self.data_home}/shlocker.json"
            path_ = Path(ofn)
            if not path_.parent.is_dir():
                os.makedirs(path_.parent)
            with open(ofn, 'w') as ofd:
                ostr = json.dumps(self._persistence, indent=4) + '\n'
                ofd.write(ostr)
            print(f"persisted to {ofn}")
            return True

        def _set_dispatch(self):
            ui = self._ui
            ui.add("clean", self.clean)
            ui.add("forget", self.forget) # unpersist;
            ui.add("help", self.help)
            ui.add("info", self.info)
            ui.add("%info", self._container_info)
            ui.add("ls", self.ls)
            ui.add("pdb", self.pdb)
            ui.add("persist", self.persist)
            ui.add("%ps", self.pstat)
            ui.add("qq", self.quitter)
            ui.add("quit", self.quitter)
            # ui.add("server", self.set_server)
            ui.add("reload", self.reload)
            ui.add("remember", self.persist)
            ui.add("restart", self.restart)
            ui.add("restore", self.restore)
            ui.add("rm", self.rm)
            ui.add("save", self.save)
            ui.add("start", self.start)
            ui.add("stop", self.stop)
            ui.add("zz", self.quitter)

        def _start__log(self, c):
            logging.info(f"Starting {c.name}:{c.id}")
            c.start()
            return True

        def _stop__log(self, c):
            logging.info(f"Stopping {c.name}:{c.id}")
            c.stop()

        def start_stop(self, which, *args):
            ui = self._ui
            if not ui.args:
                print(f"{which} needs a container identifier")
                return False
            c = self._match(ui.args[0], 'all') # start and restart need to match against stopped containers;
            print(self._view(c))
            # NONE OF THIS WORKS RIGHT!
            match which:
                case 'stop':
                    if not self.running_p(c):
                        print(self._columnize(dir(c)))
                        print(f"Can't {which} a container that in state ({c.status})")
                        return False
                    print(f'not c.stop({c.id})') ; return True
                    self.stop__log(c)
                case 'start':
                    if self.running_p(c):
                        print(f"Can't {which} a container that in state ({c.status})")
                        return False
                    print(f'not c.start({c.id})') ; return True
                    self._start__log(c)
                    time.sleep(0.5)
                    print(self._view(c))
                case 'restart':
                    if self.running_p(c):
                        print(f"([stopping {c.name}])")
                        self._stop__log(c)
                        time.sleep(2)
                    print(f"[starting {c.name}]")
                    self._start__log(c)
                    time.sleep(2)
                    print(self._view(c))
            self.load()
            return True

        def start(self, ui, *args):
            return self.start_stop("start", *args)

        def stop(self, ui, *args):
            return self.start_stop("stop", *args)

        def _view(self, c):
            visible = [ 'name', 'version' ]
            labels = [f"{k}:{c.labels[k]}" for k in visible if k in c.labels]
            # print(f"{c.name:<16s} {str(c.id)[-12:]} {c.status}  {' '.join(labels)} {c.ports} {c.top}")
            ports = self._port_mappings(c)
            mounts = self._mount_bind_mappings(c)
            return f"{c.name:<16s} ({str(c.id)[-12:]}) {ports} {mounts}"

        @property
        def all_containers(self):
            return self._docker.containers.list(all=True)

        @property
        def all_images(self):
            return self._docker.images.list(all=True)


    app = App()
    app.run()
    sys.exit(0)