#include <iostream>
#include <functional>
#include <vector>
#include <string>
#include <sstream>
#include <chrono>
#include <any>
using namespace std;
vector<vector<int>> generateIndividualNumbers(const vector<int>& nums) {
    int n = nums.size();
    vector<vector<int>> combinations;

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < nums[i]; j++) {
            vector<int> combination(n, 1);
            combination[i] = j + 1;
            combinations.push_back(combination);
        }
    }

    return combinations;
}
template<typename paramdata>
struct ParameterSweep{
    vector<paramdata> values;
    int iter;
    ParameterSweep(vector<paramdata> sweep)
    {
        values=sweep;
        iter=0;
    }
};
//template<typename paramdata>
vector<any> sweep;

struct StoredVariable {
    void* address;
    size_t size;
};

// Function to store a variable and return its address
template<typename T>
void* store(const T& variable, std::vector<StoredVariable>& storedVariables) {
    void* address = new T(variable);
    storedVariables.push_back({ address, sizeof(T) });
    return address;
}

// Specialization of the store() function for ParameterSweep struct
template<typename paramdata>
void* store(const ParameterSweep<paramdata>& variable, std::vector<StoredVariable>& storedVariables) {
    void* address = new ParameterSweep<paramdata>(variable);
    storedVariables.push_back({ address, sizeof(ParameterSweep<paramdata>) });
    return address;
}

// Function to access a stored variable using its address
template<typename T>
T* access(void* address) {
    return static_cast<T*>(address);
}

template<typename T>
void* createSweep(const std::vector<T>& vec, std::vector<StoredVariable>& storedVariables) {
    ParameterSweep<T> sweep(vec);
    return store(sweep, storedVariables);
}

class Benchmark {
public:
    Benchmark() {}
    template<typename Function, typename... Args>
    void addBenchmark(const std::string& name, Function&& func, Args&&... args) {
        benchmarks_.emplace_back(name, std::bind(std::forward<Function>(func), std::forward<Args>(args)...), std::forward<Args>(args)...);
    }
    template<typename Function>
    void addBench(const std::string& name,Function&&func)
    {
        vector<vector<int>> indices=generateIndividualNumbers(parametersizes);
        
    }
    vector<int> parametersizes;
    template <typename T>
    void initialiseParameterSweep(vector<T> vec)
    {
        createSweep(vec,storedVariables);
        parametersizes.push_back(vec.size());
    }
    std::vector<StoredVariable> storedVariables;
    void runBenchmarks() {
        for (const auto& benchmark : benchmarks_) {
            std::cout << "Running benchmark: " << benchmark.name << std::endl;

            printFunctionParameters(benchmark.parameters);

            auto start = std::chrono::high_resolution_clock::now();
            benchmark.func();
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);

            std::cout << "Execution time: " << duration.count() << " nanoseconds" << std::endl;
        }
    }

private:
    template<typename Container>
    void printFunctionParameters(const Container& params) {
        std::cout << "Function Parameters:";
        for (const auto& param : params) {
            std::cout << " " << param;
        }
        std::cout << std::endl;
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

void addflt(float a,float b,float c)
{
    float d=a+b+c;
    cout<<d<<endl;
}
int main() {
    Benchmark benchmark;

    // Add benchmarks
    //benchmark.addBenchmark("Addition", [](int a, int b) { std::cout << a + b << std::endl; }, 2, 3);
    // Add more benchmarks here
    vector<int> vec={1,2,3};
    vector<char> cc={'a','b'};
    benchmark.initialiseParameterSweep(vec);
    benchmark.initialiseParameterSweep(cc);
    cout<<benchmark.storedVariables.size();
    //benchmark.createsweep(cc);
    benchmark.addBenchmark("Float",addflt,1.0,2.0,2.0);
    benchmark.addBenchmark("Float",addflt,5.0,6.0,7.0);
    // Run benchmarks
    benchmark.runBenchmarks();

    return 0;
}
