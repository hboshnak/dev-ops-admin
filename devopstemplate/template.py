"""Create new projects from template and administer existing projects
    - defines which components/files will be installed for user requests
    - defines how components/files will be installed according to user requests
"""
import os
import logging
import json
from jinja2 import Environment, PackageLoader, select_autoescape
from jinja2 import Template
import devopstemplate.pkg as pkg
from devopstemplate.makefile import MakefileTemplate


class SkipFileError(FileExistsError):
    """Will be raised if a file that is to be created already exists and should
    be skipped according to user flags.
    """


class DevOpsTemplate():
    """Create and modify instances of the DevOps template:

    create: new instance of the template
    manage: modify an existing instance of the template
    cookiecutter: generate cookiecutter template from the devops template
    """

    def __init__(self, projectdirectory='.',
                 overwrite_exists=False, skip_exists=False, dry_run=False):
        """Provide configurations that are common to all DevOpsTemplate actions

        Params:
            projectdirectory: string with a (relative) path to the directory
                that contains the instance of the template.
            overwrite_exists: boolean specifying if existing files should be
                overwritten. An error is raised otherwise.
            skip_exists: boolean specifying if existing files should be
                skipped/ignores. An error is raised otherwise.
            dry_run: boolean specifying whether to not perform any actions in
                order to see (in the log) what would have happend.
        """
        self.__projectdir = projectdirectory
        self.__overwrite = overwrite_exists
        self.__skip = skip_exists
        self.__dry_run = dry_run
        with pkg.stream('template.json') as fh:
            self.__template_dict = json.load(fh)
        self.__template_dname = 'template'
        self.__env = Environment(loader=PackageLoader(__name__,
                                                      self.__template_dname),
                                 autoescape=select_autoescape(default=True))
        # Create project base directory if not present
        self.__mkdir(projectdirectory)

    def create(self, projectconfig):
        """Create a new project from the DevOps template given config options.

        Installs components which are defined in template.json

        Params:
            projectconfig: Dictionary with configuration flags supported by the
                template (typically generated by the CLI, see main.create)
        """
        logger = logging.getLogger('DevOpsTemplate.create')
        logger.info('Create project from template')
        logger.info('Project name: %s', projectconfig['project_name'])
        # Create empty directories for now. Could be replaced with files
        # defined in template.json in future.
        logger.debug('  scripts directory: %s',
                     projectconfig['add_scripts_dir'])
        if projectconfig['add_scripts_dir']:
            self.__mkdir('scripts')
        logger.debug('  docs directory:    %s',
                     projectconfig['add_docs_dir'])
        if projectconfig['add_docs_dir']:
            self.__mkdir('docs')
        # Install files from components which are part of every template
        self.__install('src', projectconfig)
        self.__install('tests', projectconfig)
        self.__install('make', projectconfig)
        self.__install('setuptools', projectconfig)
        self.__install('docker', projectconfig)
        # Install files from components according to config options provided
        # by user
        logger.debug('  .gitignore file:   %s',
                     not projectconfig['no_gitignore_file'])
        if not projectconfig['no_gitignore_file']:
            self.__install('git', projectconfig)
        logger.debug('  README.md file:    %s',
                     not projectconfig['no_readme_file'])
        if not projectconfig['no_readme_file']:
            self.__install('readme', projectconfig)
        logger.debug('  SonarQube support: %s',
                     not projectconfig['no_sonar'])
        use_sonar = not projectconfig['no_sonar']
        if use_sonar:
            self.__install('sonar', projectconfig)
        self.__configure_makefile(use_sonar=use_sonar)

    def cookiecutter(self, projectconfig):
        """Create a new cookiecutter template from the DevOps template given
        config options. Config options only affect the default values for the
        cookiecutter template, which are provided in cookiecutter.json

        Generates components which are defined in template.json

        Params:
            projectconfig: Dictionary with configuration flags supported by the
                template (flags are defined in ProjectConfig.cookiecutter and
                can be modified based on command-line args, see
                main.cookiecutter)
        """
        logger = logging.getLogger('DevOpsTemplate.cookiecutter')
        logger.info('Generate cookiecutter template')
        # Generate cookiecutter.json
        # configuration is provided by the projectconfig dictionary
        cookiecutter_json_fpath = os.path.join(self.__projectdir,
                                               'cookiecutter.json')
        try:
            self.__check_project_file(cookiecutter_json_fpath)
            if not self.__dry_run:
                with open(cookiecutter_json_fpath, 'w') as fh:
                    json.dump(projectconfig, fh, indent=2)
            logger.info('project:%s', cookiecutter_json_fpath)
        except SkipFileError:
            logger.warning('File %s exists, skipping', cookiecutter_json_fpath)

        # Generate cookiecutter README.md
        readme_fpath = os.path.join(self.__projectdir, 'README.md')
        try:
            self.__check_project_file(readme_fpath)
            if not self.__dry_run:
                with open(readme_fpath, 'w') as fh:
                    readme_content_list = ['# Cookiecutter Template']
                    fh.writelines(readme_content_list)
            logger.info('project:%s', readme_fpath)
        except SkipFileError:
            logger.warning('File %s exists, skipping', readme_fpath)

        # Generate hooks directory with pre/post generation scripts if required
        # (might be useful in future)
        #
        # Generate project template
        cookiecutter_project_dname = '{{cookiecutter.project_slug}}/'
        self.__mkdir(cookiecutter_project_dname)
        # Adjust projectdirectory such that __install installs to the correct
        # directory (projectdirectory represents cookiecutter template root)
        cookiecutter_rootdir = self.__projectdir
        self.__projectdir = os.path.join(self.__projectdir,
                                         cookiecutter_project_dname)
        # Generate cookiecutterconfig for rendering cookiecutter template
        # variables
        cookiecutterconfig = {key: '{{cookiecutter.%s}}' % key
                              for key in projectconfig.keys()}
        # Install all template components
        components = ['src',
                      'tests',
                      'make',
                      'setuptools',
                      'git',
                      'readme',
                      'docker',
                      'sonar']
        for comp in components:
            self.__install(comp, cookiecutterconfig)

        # Revert project directory to cookiecutter root directory
        self.__projectdir = cookiecutter_rootdir

    def manage(self, projectconfig):
        """Add functionality/components to an existing project that has been
        created from the DevOps template given configuration options.

        Params:
            projectconfig: Dictionary with configuration flags supported by the
                template (typically generated by the CLI, see main.manage)
        """
        logger = logging.getLogger('DevOpsTemplate.manage')
        # Create empty directories for now. Could be replaced with files
        # defined in template.json in future.
        logger.debug('  scripts directory: %s',
                     projectconfig['add_scripts_dir'])
        if projectconfig['add_scripts_dir']:
            self.__mkdir('scripts')
        logger.debug('  docs directory:    %s',
                     projectconfig['add_docs_dir'])
        if projectconfig['add_docs_dir']:
            self.__mkdir('docs')
        logger.debug('  .gitignore file:   %s',
                     projectconfig['add_gitignore_file'])
        if projectconfig['add_gitignore_file']:
            self.__install('git', projectconfig)
        logger.debug('  README.md file:    %s',
                     projectconfig['add_readme_file'])
        if projectconfig['add_readme_file']:
            self.__install('readme', projectconfig)
        logger.debug('  SonarQube support: %s',
                     projectconfig['add_sonar'])
        if projectconfig['add_sonar']:
            self.__install('sonar', projectconfig)
            self.__configure_makefile(use_sonar=True)

    def __install(self, template_component, context):
        """Copy and render files for a template component
        Components, i.e., file to install, are defined in 'template.json' which
        is represented by __template_dict.

        Params:
            template_component: String specifying the component to install.
            context: Dictionary with the context for rendering Jinja2
                templates.
        """
        file_list = self.__template_dict[template_component]
        for template_fpath in file_list:
            # Render file path (paths can contain template variables)
            project_fpath = Template(template_fpath).render(**context)
            self.__render(template_fpath, project_fpath, context)

    def __mkdir(self, project_dname):
        """Create a directory within the project if not present

        Params:
            project_dname: String specifying the name of the directory
        """
        logger = logging.getLogger('DevOpsTemplate.__mkdir')
        project_dpath = os.path.join(self.__projectdir, project_dname)
        if not os.path.exists(project_dpath):
            logger.info('creating directory: %s', project_dpath)
            if not self.__dry_run:
                os.makedirs(project_dpath)
        else:
            logger.debug('directory %s exists', project_dpath)

    def __render(self, pkg_fname, project_fname, context):
        """Render template to project according to overwrite/skip class members
        The source file will be used as a Jinja2 template and rendered before
        the rendering result will be written to the target file.

        Params:
            pkg_fname: String specifying the file in the distribution package
            project_fname: String specifying the target file in the project
            context: Dictionary with the context for rendering Jinja2 templates
        Raises:
            FileNotFoundError: If pkg_fname is not available
            FileExistsError: If project_fname already exists in the project
                and skip-exists=False, overwrite-exists=False
        """
        logger = logging.getLogger('DevOpsTemplate.__render')
        pkg_fpath = os.path.join(self.__template_dname, pkg_fname)
        if not pkg.exists(pkg_fpath):
            raise FileNotFoundError(f'File {pkg_fpath} not available in '
                                    'distribution package')
        project_fpath = os.path.join(self.__projectdir, project_fname)
        try:
            self.__check_project_file(project_fpath)
        except SkipFileError:
            logger.warning('File %s exists, skipping', project_fpath)
            return
        if not self.__dry_run:
            # Create parent directories if not present
            parent_dname = os.path.dirname(project_fpath)
            if not os.path.exists(parent_dname):
                os.makedirs(parent_dname)
            # Copy file in binary mode
            # with pkg.stream(pkg_fname) as pkg_fh:
            #     with open(project_fpath, 'wb') as project_fh:
            #         shutil.copyfileobj(pkg_fh, project_fh)
            template = self.__env.get_template(pkg_fname)
            with open(project_fpath, 'w') as project_fh:
                template.stream(**context).dump(project_fh)
        logger.info('template:%s  ->  project:%s', pkg_fname, project_fpath)

    def __check_project_file(self, project_fpath):
        """Check whether the given file can be created in the project without
        conflict. A conflict arises if the file exists and should not be
        skipped or overwritten.

        Params:
            project_fpath: String specifying the path to the file in the
                project.
        Returns: True if the file can be created without conflict.
        Raises:
            SkipFileError: if the creation of the new file should be skipped.
            FileExistsError: if the file that should be created already exists
                and should not be overwritten.
        """
        if os.path.exists(project_fpath) and self.__skip:
            raise SkipFileError(f'File {project_fpath} already exists, skip.')
        if os.path.exists(project_fpath) and not self.__overwrite:
            raise FileExistsError(f'File {project_fpath} already exists, exit.'
                                  ' (use --skip-exists or --overwrite-exists'
                                  ' to control behavior)')
        return True

    def __configure_makefile(self, use_sonar):
        """Re-writes Makefile with configuration options:

        Params:
            use_sonar: Boolean setting whether to use SonarQube reporting
                during multi-stage docker build (within first 'build' stage)
        """
        var_value_dict = {}
        var_value_dict['DOCKERSONAR'] = 'True' if use_sonar else 'False'
        # Load installed Makefile
        with open(os.path.join(self.__projectdir, 'Makefile'), 'r+') as fh:
            mktemplate = MakefileTemplate(fh)
            fh.seek(0)
            mktemplate.write(fh,
                             var_value_dict=var_value_dict)
            fh.truncate()
