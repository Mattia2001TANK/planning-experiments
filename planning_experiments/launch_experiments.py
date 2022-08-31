import json
import os
import os.path as path
import sys
import random
import datetime
import click
from planning_experiments import constants
from planning_experiments.constants import *
from planning_experiments.experiment_environment import Domain, ExperimentEnviorment


def collect_instances(instances_path):
    pddl_domains = []
    pddl_instances = []
    for file in os.listdir(instances_path):
        if PDDL_EXTENSION in file:
            if DOMAIN_STR_CONST in file:
                pddl_domains.append(file)
            else:
                pddl_instances.append(file)
    if len(pddl_domains) != 1 and len(pddl_domains) != len(pddl_instances):
        raise Exception(DOMAIN_INSTANCES_ERROR)
    pddl_instances.sort()
    pddl_domains.sort()
    pairs = []
    for i in range(len(pddl_instances)):
        if len(pddl_domains) == 1:
            pairs.append((pddl_domains[0], pddl_instances[i]))
        else:
            assert '-' in pddl_domains[i] or '_' in pddl_domains[i]
            if '-' in pddl_domains[i]:
                sep = '-'
            elif '_' in pddl_domains[i]:
                sep = '_'
            else:
                assert False, 'ABORTING!'
            test_soundness = pddl_domains[i].split(sep)[1]
            #assert test_soundness == pddl_instances[i]
            pairs.append((pddl_domains[i], pddl_instances[i]))
    return pairs


def scripts_setup(name):
    # Clean old scripts with the same name
    script_folder = path.join(SCRIPTS_FOLDER, name)
    if path.isdir(script_folder):
        os.system(RM_CMD.format(script_folder))
    #######################################
    os.makedirs(script_folder)
    return script_folder


def create_results_folder(env: ExperimentEnviorment, exp_id: str, planner: str, config: str, domain: str, results_file: str):
    top_level_folder = path.join(env.result_folder, env.name)
    if not path.isdir(top_level_folder):
        os.makedirs(top_level_folder)

    results_folder = path.join(
        top_level_folder, EXPERIMENT_RUN_FOLDER.format(exp_id))
    if not path.isdir(results_folder):
        os.mkdir(results_folder)

    results_folder_planner = path.join(
        results_folder, '{}_{}'.format(planner, config))
    if not path.isdir(results_folder_planner):
        os.mkdir(results_folder_planner)

    if not path.exists(results_file):
        os.system('touch {}'.format(results_file))

    results_folder_planner_domain = path.join(results_folder_planner, domain)
    os.mkdir(results_folder_planner_domain)

    return path.abspath(results_folder_planner_domain)


def manage_planner_copy(name, planner, config, domain, instance, exp_id, script_str):
    tmp_dir = path.join(PLANNERS_FOLDER, planner, PLANNER_COPIES_FOLDER)
    if not path.isdir(tmp_dir):
        os.mkdir(tmp_dir)
    copy_planner_dst = path.join(tmp_dir,
                                 'copy_{name}_{planner}_{config}_{domain}_{instance}_{exp_id}'
                                 .format(name=name, planner=planner, config=config, domain=domain, instance=instance, exp_id=exp_id))
    planner_source = path.join(PLANNERS_FOLDER, planner, SOURCE_FOLDER)
    script_str = script_str.replace(
        PLANNER_DESTINATION, path.abspath(copy_planner_dst))
    script_str = script_str.replace(
        PLANNER_SOURCE, path.abspath(planner_source))

    return script_str


def write_script(shell_script, script_name, script_dst):
    script_path = path.join(script_dst, script_name)
    with open(script_path, 'w') as output_writer:
        output_writer.write(shell_script)


def create_scripts(environment: ExperimentEnviorment, exp_id: str, short_name: str):
    script_list = []
    script_folder = scripts_setup(environment.name)

    results_file = path.join(path.join(
        environment.result_folder, environment.name), EXPERIMENT_RUN_FOLDER.format(exp_id), 'results.txt')

    for planner in environment.run_dictionary.keys():
        for config in environment.run_dictionary[planner][CONFIGS]:
            for domain in environment.run_dictionary[planner][DOMAINS]:
                assert isinstance(domain, Domain)
                solution_folder = create_results_folder(
                    environment, exp_id, planner, config, domain.name, results_file)
                    
                for pddl_domain, pddl_instance in collect_instances(domain.path):

                    instance_name = pddl_instance.replace(PDDL_EXTENSION, '')
                    solution_name = '{}_{}.sol'.format(domain, instance_name)
                    script_name = '{}_{}_{}_{}_{}.sh'.format(
                        environment.name, planner, config, domain.name, instance_name)
                    shell_script = SHELL_TEMPLATE

                    path_to_pddl_domain = path.join(domain.path, pddl_domain)
                    path_to_pddl_instance = path.join(domain.path, pddl_instance)

                    command_template = cfg_map[config]
                    planner_exe = command_template.replace(PLANNER_EXE_DOMAIN, path_to_pddl_domain) \
                        .replace(PLANNER_EXE_INSTANCE, path_to_pddl_instance) \
                        .replace(PLANNER_EXE_SOLUTION, path.join(solution_folder, solution_name))

                    stde = path.abspath(
                        path.join(solution_folder, 'err_{}_{}.txt'.format(domain, instance_name)))
                    stdo = path.abspath(
                        path.join(solution_folder, 'out_{}_{}.txt'.format(domain, instance_name)))
                    planner_exe += " 2>> {} 1>> {}".format(stde, stdo)

                    shell_script = manage_planner_copy(
                        name, planner, config, domain, instance_name, exp_id, shell_script)
                    shell_script = shell_script.replace(
                        MEMORY_SHELL, str(memory))
                    shell_script = shell_script.replace(TIME_SHELL, str(time))
                    shell_script = shell_script.replace(
                        PLANNER_EXE_SHELL, planner_exe)

                    path_to_collect = path.abspath(
                        path.join(COLLECT_DATA_FOLDER, run_dict[planner][COLLECT_DATA]))
                    shell_script = shell_script.replace(
                        SHELL_COLLECT_DATA, path_to_collect)

                    if DOMAINS4VAL not in run_dict[planner].keys() or domain not in run_dict[planner][DOMAINS4VAL]:
                        val = NO_VALIDATION_PERFORMED
                    else:
                        domain4val = run_dict[planner][DOMAINS4VAL].get(
                            domain, NO_VALIDATION_PERFORMED)
                        path_to_domain4val = path.join(
                            path_to_domains, domain4val, pddl_domain)
                        path_to_instance4val = path.join(
                            path_to_domains, domain4val, pddl_instance)
                        val = '{}#{}'.format(
                            path_to_domain4val, path_to_instance4val)

                    shell_script = shell_script\
                        .replace(SHELL_SOL_FILE, path.join(solution_folder, solution_name))\
                        .replace(SHELL_SOL_INSTANCE, instance_name)\
                        .replace(SHELL_SOL_DOMAIN, domain)\
                        .replace(SHELL_STDO, stdo).replace(SHELL_STDE, stde)\
                        .replace(SHELL_RESULTS, path.abspath(results_file))\
                        .replace(SHELL_SYSTEM, '{}_{}'.format(planner, config))\
                        .replace(SHELL_DOMAIN4VAL, val)
                    write_script(shell_script, script_name, script_folder)
                    script_list.append((script_name.replace(
                        '.sh', ''), path.join(script_folder, script_name)))

    return script_list


def delete_old_planners(cfg_dict):
    for planner in cfg_dict.keys():
        copies_folder = path.join(
            PLANNERS_FOLDER, planner, PLANNER_COPIES_FOLDER)
        if path.isdir(copies_folder):
            os.system(RM_CMD.format(copies_folder))


def execute_scripts(name, script_list, ppn, priority, no_qsub):
    # Qsub logs setup
    log_dst = path.join(LOG_FOLDER, name)
    if path.isdir(log_dst):
        os.system(RM_CMD.format(log_dst))
    os.mkdir(log_dst)
    #################

    if no_qsub:
        for (script_name, script) in script_list:
            os.system(f'chmod +x {script}')
            os.system(script)
    else:
        for (script_name, script) in script_list:
            qsub_cmd = QSUB_TEMPLATE
            stdo = path.join(LOG_FOLDER, name, 'log_{}'.format(script_name))
            stde = path.join(LOG_FOLDER, name, 'err_{}'.format(script_name))
            qsub_cmd = qsub_cmd\
                .replace(PPN_QSUB, str(ppn))\
                .replace(PRIORITY_QSUB, str(priority))\
                .replace(SCRIPT_QSUB, script)\
                .replace(LOG_QSUB, stdo)\
                .replace(ERR_QSUB, stde)
            print(qsub_cmd)
            os.system(qsub_cmd)


def copy_elaborate_data(exp_id, name):
    results_folder = path.join(
        path.join(RESULTS_FOLDER, name), EXPERIMENT_RUN_FOLDER.format(exp_id))
    os.system('cp ./elaborate_data.py {}'.format(results_folder))


@click.command()
@click.argument('cfg')
@click.option('--short_name', '-n', default='')
@click.option('--no-qsub', is_flag=True)
def main(cfg, short_name, no_qsub):
    cfg_dict = json.load(open(cfg, ))
    run_dict = cfg_dict[PLANNERS_X_DOMAINS]
    delete_old_planners(run_dict)
    name = cfg_dict[NAME]
    exp_id = short_name + str(datetime.datetime.now()).replace(' ',
                                                               '_') + '_{}'.format(str(random.randint(0, sys.maxsize)))
    path_to_domains = cfg_dict[PATH_TO_DOMAINS]
    memory = cfg_dict[MEMORY]
    time = cfg_dict[TIME]

    collect_runs(run_dict, path_to_domains)

    script_list = create_scripts(
        name, exp_id, run_dict, memory, time, path_to_domains, short_name)

    execute_scripts(name, script_list, cfg_dict[PPN], cfg_dict[PRIORITY], no_qsub)

    #copy_elaborate_data(exp_id, name)


class Executor:

    def __init__(self, environment: ExperimentEnviorment, short_name = '') -> None:
        self.environment = environment
        self.short_name = short_name

    # def delete_old_planners(self):
    #     for planner in self.environment.run_dictionary:
    #         copies_folder = path.join(
    #             self.environment.systems_folder, PLANNER_COPIES_FOLDER)
    #         if path.isdir(copies_folder):
    #             os.system(RM_CMD.format(copies_folder))

    def run_experiments(self):
        exp_id = self.short_name + str(datetime.datetime.now()).replace(' ', '_') + '_{}'.format(str(random.randint(0, sys.maxsize)))
        script_list = create_scripts(self.environment, exp_id, self.short_name)

if __name__ == '__main__':
    main()
