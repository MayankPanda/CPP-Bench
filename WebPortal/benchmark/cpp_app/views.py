from django.shortcuts import render
import os
import subprocess
from django.shortcuts import render
from django.http import FileResponse
from .forms import CppCodeForm
from .models import Benchmark
from django.conf import settings

DOCKER_IMAGE_NAME = "gcc"

BENCHMARK_CLASS_CODE = '''
#include <iostream>
#include <functional>
#include <vector>
#include <string>
#include <sstream>
#include <chrono>
#include <fstream>
using namespace std;

class Benchmark {
public:
    Benchmark() {}

    template<typename Function, typename... Args>
    void addBenchmark(const std::string& name, Function&& func, Args&&... args) {
        benchmarks_.emplace_back(name, std::bind(std::forward<Function>(func), std::forward<Args>(args)...), std::forward<Args>(args)...);
        // Update the maximum number of parameters for all benchmarks
        maxParameters = std::max(maxParameters, sizeof...(Args));
    }

    void runBenchmarks() {
        std::ofstream outputFileStream("results.csv");

        // Check if the CSV file is empty
        outputFileStream.seekp(0, std::ios::end);
        if (outputFileStream.tellp() == 0) {
            outputFileStream << "Benchmark Name";
            for (size_t i = 0; i < maxParameters; ++i) {
                outputFileStream << ",Parameter " << i + 1;
            }
            outputFileStream << ",Execution Time (ns)" << std::endl;
        }

        for (const auto& benchmark : benchmarks_) {
            std::streambuf* originalStdout = std::cout.rdbuf();
            std::cout.rdbuf(outputFileStream.rdbuf());
            std::cout << benchmark.name;

            printFunctionParameters(benchmark.parameters);

            auto start = std::chrono::high_resolution_clock::now();
            benchmark.func();
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);

            std::cout << "," << duration.count() << std::endl;
            std::cout.rdbuf(originalStdout);
        }
        outputFileStream.close();
    }


private:
    size_t maxParameters = 0; // Maximum number of parameters for all benchmarks

    template<typename Container>
    void printFunctionParameters(const Container& params) {
        for (const auto& param : params) {
            std::cout << "," << param;
        }

        // Fill empty cells if the number of parameters is less than maxParameters
        size_t remainingParams = maxParameters - params.size();
        for (size_t i = 0; i < remainingParams; ++i) {
            std::cout << ",";
        }
    }

    struct BenchmarkData {
        std::string name;
        std::function<void()> func;
        std::vector<std::string> parameters;

        template<typename Function, typename... Args>
        BenchmarkData(const std::string& n, Function&& f, Args&&... args)
            : name(n), func(std::forward<Function>(f)) {
            parameters.reserve(sizeof...(Args));
            std::ostringstream oss;
            ((oss << args << " "), ...);
            std::istringstream iss(oss.str());
            std::string param;
            while (iss >> param) {
                parameters.push_back(param);
            }
        }
    };

    std::vector<BenchmarkData> benchmarks_;
};
'''

def run_cpp_code_with_csv_output(partial_cpp_code, compiler='gcc'):
    # Map user's compiler choice to the corresponding Docker image
    compiler_images = {
        'gcc': 'gcc',
        'clang': 'clang',
        'mingw': 'keryi/mingw-gcc',  # Docker image for MinGW-w64
        'msvc': 'mcr.microsoft.com/windows/nanoserver',  # Docker image for MSVC
        # Add more compiler options and their corresponding Docker images here
    }

    # Check if the user's compiler choice is supported
    if compiler not in compiler_images:
        return {"error": f"Compiler '{compiler}' is not supported."}

    # Get the Docker image name for the chosen compiler
    docker_image = compiler_images[compiler]

    if compiler == 'msvc':
        compile_command = ['cl', '/EHsc', '/Fotemp', '/Feapp', 'temp.cpp']
        run_command = ['.\\app']
    else:
        compile_command = ['g++', '/app/temp.cpp', '-o', '/app/temp']
        run_command = ['./temp']

    # Write the C++ code to a temporary file
    cpp_code=BENCHMARK_CLASS_CODE+ '\n' + partial_cpp_code
    with open('temp.cpp', 'w') as f:
        f.write(cpp_code)

    try:
        # Run the C++ code inside a Docker container
        subprocess.run(['docker', 'run', '--rm', '-v', f'{os.getcwd()}:/app', '-w', '/app', DOCKER_IMAGE_NAME] + compile_command, check=True)
        completed_process = subprocess.run(['docker', 'run', '--rm', '-v', f'{os.getcwd()}:/app', '-w', '/app', DOCKER_IMAGE_NAME] + run_command, check=True, capture_output=True, text=True)

        output = completed_process.stdout.strip()

        # Optionally, you can read the output CSV file content directly from the container
        csv_data = subprocess.run(
    ['docker', 'run', '--rm', '-v', f'{os.getcwd()}:/app', '-w', '/app', DOCKER_IMAGE_NAME, 'cat', '/app/output.csv'],
    capture_output=True,
    text=True
)

        # Remove temporary C++ file
        os.remove('temp.cpp')
        if compiler == 'msvc':
            os.remove('app.exe')
        else:
            os.remove('temp')

        # Prepare the response with the output and CSV data
        result = {"output": output}

        # Add the CSV data to the result
        result["csv_data"] = csv_data.stdout.strip()

        return result

    except subprocess.CalledProcessError as e:
        # If the subprocess returns an error, capture the error message
        error_output = e.stderr.strip() if e.stderr else e.stdout.strip()
        return {"error": error_output}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout error. The code took too long to execute."}
    except Exception as e:
        return {"error": str(e)}
    
def index(request):
    if request.method == 'POST':
        form = CppCodeForm(request.POST)
        if form.is_valid():
            cpp_code = form.cleaned_data['cpp_code']
            identifier = form.cleaned_data['identifier']  # Get the identifier from the form

            result = run_cpp_code_with_csv_output(cpp_code)

            # Check if the code execution resulted in an error
            if 'error' in result:
                context = {'form': form, 'error_message': result['error']}
            else:
                # Check if the required keys exist in the result dictionary
                benchmark = Benchmark(identifier=identifier, csv_file=result['csv_data'])
                benchmark.save()

                # Retrieve all saved benchmarks from the database
                benchmarks = Benchmark.objects.all()

                # Provide the download link for the latest benchmark (the one just created)
                latest_benchmark = benchmarks.latest('id')

                csv_file_path = latest_benchmark.csv_file.url

                context = {'form': form, 'output': result['output'], 'csv_file_path': csv_file_path, 'benchmarks': benchmarks}

    else:
        form = CppCodeForm()
        context = {'form': form}

    return render(request, 'index.html', context)

def previous_benchmarks(request):
    # Get all the saved benchmarks from the database
    benchmarks = Benchmark.objects.all()

    return render(request, 'previous_benchmarks.html', {'benchmarks': benchmarks})

def download_csv(request, benchmark_id):
    try:
        # Get the benchmark from the database
        benchmark = Benchmark.objects.get(id=benchmark_id)

        # Check if the CSV file exists
        if benchmark.csv_file and os.path.exists(benchmark.csv_file.path):
            # Prepare and send the response with the CSV file
            with open(benchmark.csv_file.path, 'rb') as csv_file:
                response = FileResponse(csv_file, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(benchmark.csv_file.path)}"'
                return response
        else:
            return render(request, 'previous_benchmarks.html', {'error_message': 'CSV file not found.'})
    except Benchmark.DoesNotExist:
        return render(request, 'previous_benchmarks.html', {'error_message': 'Benchmark not found.'})
# Create your views here.
