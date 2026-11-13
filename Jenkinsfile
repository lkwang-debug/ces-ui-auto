pipeline {
    agent { label 'windows-ui' }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        UIAUTO_HEADLESS = '1'
        UIAUTO_WINDOW_SIZE = '1920,1080'
        ALLURE_RESULTS = 'allure-results'
        ALLURE_REPORT = 'allure-report'
        PYTHON_EXE = 'D:\\pycharm\\PythonProject\\.venv1\\Scripts\\python.exe'
        CHROMEDRIVER_PATH = 'D:\\pycharm\\PythonProject\\.venv1\\Scripts\\chromedriver.exe'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Environment Check') {
            steps {
                powershell '''
                    & "$env:PYTHON_EXE" --version
                    & "$env:PYTHON_EXE" -m pytest --version
                    if (Get-Command allure -ErrorAction SilentlyContinue) {
                        allure --version
                    } else {
                        Write-Host "Allure commandline not found. Jenkins Allure plugin can still publish allure-results if configured."
                    }
                '''
            }
        }

        stage('Run UI Tests') {
            steps {
                powershell '''
                    $env:UIAUTO_HEADLESS = "$env:UIAUTO_HEADLESS"
                    $env:UIAUTO_WINDOW_SIZE = "$env:UIAUTO_WINDOW_SIZE"
                    $env:CHROMEDRIVER_PATH = "$env:CHROMEDRIVER_PATH"
                    & "$env:PYTHON_EXE" -m pytest -q --disable-warnings
                '''
            }
        }
    }

    post {
        always {
            script {
                if (fileExists(env.ALLURE_RESULTS)) {
                    allure([
                        includeProperties: false,
                        jdk: '',
                        properties: [],
                        reportBuildPolicy: 'ALWAYS',
                        results: [[path: env.ALLURE_RESULTS]]
                    ])
                }
            }

            archiveArtifacts artifacts: 'screenshots/**/*.png, allure-results/**/*, allure-report/**/*', allowEmptyArchive: true

            withCredentials([string(credentialsId: 'feishu-ui-auto-webhook', variable: 'FEISHU_WEBHOOK')]) {
                powershell '''
                    $env:ALLURE_REPORT_URL = "$env:BUILD_URL" + "allure/"
                    & "$env:PYTHON_EXE" scripts\\feishu_notify.py --results-dir "$env:ALLURE_RESULTS"
                '''
            }
        }
    }
}
