#!/bin/env python3.13
"""shlocker is a docker container management tool;"""

if True:
    import docker
    from   functools import partial
    import json
    import os
    from   logger import logging
    from   pathlib import Path
    import pdb
    import platformdirs
    from   pprint import pprint, pformat
    import re
    import subprocess
    import sys

    # sys.path.insert(1, ".")
    from tui3 import Tui3


class ServerClient:
    SERVER = "http://localhost:6502"

    def __init__(self):
        pass

if __name__ == "__main__":
    class App:
        LOGFILE = "/var/log/shlocker"
        REXHEX = re.compile(r'[0-9a-fA-F]+')
        def __init__(self):
            self.data_home = platformdirs.user_data_dir("shlocker", "mr.wook@gmail.com")
            self._width = self._get_width()
            self._logger_setup()
            self._ui = Tui3(prompt="shlocker> ")
            self._set_dispatch()
            self._docker = docker.from_env()
            self.reload()
            self._persistence = self.load()
            return

        def _columnize(self, list_):
            max_col_width = max([len(item) for item in list_]) + 1
            n_cols = (self._width // max_col_width) -1
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
            log_file = "/var/www/shlocker/shlocker.log"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            logging.basicConfig(filename=log_file, filemode='a',  # append mode
                                format='%(asctime)s [%(levelname)s] %(message)s',
                                level=logging.INFO)  # or DEBUG, WARNING, etc.
            # logging.info("Shlock logger initialized.")

        def ls(self, ui, *args):
            self.reload()
            which = [ 'running' ]
            if '--all' in args:
                which = list(self._by_state.keys())
            visible = [ 'name', 'version' ]
            for state in which:
                print(state.upper())
                for c in self._by_state[state]:
                    view = self._view(c)
                    print(view)
            return True

        def _match(self, id_or_name, containers = None):
            if containers is None:
                containers = self._by_state['running']
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

        def persist(self, ui, *args):
            containers = self._by_state['running']
            if not containers:
                print(f"No running containers, nothing to persist")
                return False
            if args == ( None, ):   # No args artifact;
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
            return True

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

        def reload(self, *args):
            self._all_containers = all_ = self._docker.containers.list(all=True)
            states = list(set([c.status for c in all_]))
            self._by_state = dict()
            for state in states:
                self._by_state[state] = [c for c in all_ if c.status == state]
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
            ui.add("info", self.info)
            ui.add("%info", self._container_info)
            ui.add("ls", self.ls)
            ui.add("persist", self.persist)
            ui.add("%ps", self.pstat)
            ui.add("qq", self.quitter)
            ui.add("quit", self.quitter)
            ui.add("save", self.save)
            # ui.add("server", self.set_server)
            ui.add("reload", self.reload)
            ui.add("restart", partial(self.start_stop, "restart", *ui.args))
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
            if args == ( None, ):
                print(f"{which} needs a container identifier")
                return False
            c = self._match(args[0])
            print(str(c))
            # Convert this to match which;
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
                    if not self.running_p(c):
                        self._start__log(c)
                    else:
                        self._stop__log(c)
                        time.sleep(2)
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
            labels = [f"{k}:{c.labels[k]}" for k in visible if k in c.labels]
            # print(f"{c.name:<16s} {str(c.id)[-12:]} {c.status}  {' '.join(labels)} {c.ports} {c.top}")
            ports = self._port_mappings(c)
            mounts = self._mount_bind_mappings(c)
            return f"{c.name:<16s} ({str(c.id)[-12:]}) {ports} {mounts}"

    app = App()
    app.run()
    sys.exit(0)