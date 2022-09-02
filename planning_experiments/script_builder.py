from os import path
from planning_experiments.experiment_environment import ExperimentEnviorment, System


class ScriptBuilder:

    BASH = "#!/bin/bash"
    PWD = "var=$PWD"

    def __init__(self, env: ExperimentEnviorment, system: System, system_dst: str, time: int, 
                       system_exe: str, collect_data_cmd: str, stdo: str, stde: str, script_name: str, 
                       script_folder: str, memory: int = None) -> None:
        self.system = system
        self.enviorment = env
        self.inner_script = []
        self.outer_script = []
        self.memory = memory
        self.system_dst = system_dst
        self.time = time
        self.system_exe = system_exe
        self.collect_data_cmd = collect_data_cmd
        self.stdo = stdo
        self.stde = stde
        self.script_name = script_name
        self.script_folder = script_folder
        
    def get_script(self):
        self.outer_script.append(self.BASH)
        self.outer_script.append(self.PWD)

        self.outer_script.append(f'mkdir {self.system_dst}')

        self.manage_dependencies()
        self.outer_script.append(f'cd {self.system_dst}')

        self.outer_script.append(f'/usr/bin/time -f "Total Runtime: %e" timeout --signal=HUP {self.time} bash -i {path.join(self.script_folder, self.script_name)} 2>> {self.stde} 1>> {self.stdo}')
        
        ## INNER SCRIPT ##
        self.inner_script.append(self.BASH)
        
        if self.enviorment.conda_env is not None:
            self.inner_script.append(f'conda activate {self.enviorment.conda_env}')
        
        exe_str = self.manage_complex_cmd()
        
        if self.memory is not None:
            self.inner_script.append(f'ulimit -v {self.memory}')
        
        self.inner_script.append(exe_str)
        
        #################
        self.outer_script.append(self.collect_data_cmd)
        if self.enviorment.delete_systems:
            self.outer_script.append(f'rm -r -f {self.system_dst}')
        
        inner_script_str = '\n'.join(self.inner_script)
        outer_script_str = '\n'.join(self.outer_script)
        return inner_script_str, outer_script_str
    
    def set_memory(self, memory: int):
        self.memory = memory

    def manage_dependencies(self):
        dependencies = set([dep for dep in self.system.get_dependencies()])
        for dep in dependencies:
            self.outer_script.append(f'cp -r {path.abspath(dep)} {self.system_dst}')
    
    def manage_complex_cmd(self):
        if isinstance(self.system_exe, list):
            cmd_chain = []
            for cmd in self.system_exe:
                cmd_chain.append(cmd)
            return '\n'.join(cmd_chain)
        else:
            exe_str = self.system_exe
        return exe_str

