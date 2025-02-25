
#include <omnitrace/user.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>
#include <vector>

void
print_info(const char* _name)
{
    fflush(stdout);
    fflush(stderr);
    printf("[%s] pid = %i, ppid = %i\n", _name, getpid(), getppid());
    fflush(stdout);
    fflush(stderr);
}

int
run(const char* _name, int nchildren)
{
    auto _threads = std::vector<std::thread>{};
    for(int i = 0; i < nchildren; ++i)
    {
        omnitrace_user_push_region("launch_child");
        auto _run = [i, _name]() {
            pid_t _pid = fork();
            if(_pid == 0)
            {
                // child code
                print_info(_name);
                auto _sleep = [=]() {
                    std::this_thread::sleep_for(std::chrono::seconds{ i + 1 });
                };
                std::thread{ _sleep }.join();
                exit(EXIT_SUCCESS);
            }
        };
        _threads.emplace_back(_run);
        omnitrace_user_pop_region("launch_child");
    }

    omnitrace_user_push_region("wait_for_children");

    int   _status   = 0;
    pid_t _wait_pid = 0;
    // parent waits for all the child processes
    while((_wait_pid = wait(&_status)) > 0)
    {
        printf("[%s][%i] returned from wait with pid = %i :: ", _name, getpid(),
               _wait_pid);
        if(WIFEXITED(_status))
        {
            printf("exited, status=%d\n", WEXITSTATUS(_status));
        }
        else if(WIFSIGNALED(_status))
        {
            printf("killed by signal %d\n", WTERMSIG(_status));
        }
        else if(WIFSTOPPED(_status))
        {
            printf("stopped by signal %d\n", WSTOPSIG(_status));
        }
        else if(WIFCONTINUED(_status))
        {
            printf("continued\n");
        }
        else
        {
            printf("unknown\n");
        }
    }

    for(auto& itr : _threads)
        itr.join();

    omnitrace_user_pop_region("wait_for_children");
    return _status;
}

int
main(int argc, char** argv)
{
    int _n = 4;
    if(argc > 1) _n = std::stoi(argv[1]);

    print_info(argv[0]);
    return run(argv[0], _n);
}
