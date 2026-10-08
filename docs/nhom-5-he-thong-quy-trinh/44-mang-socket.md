# Bài 44 — Mạng: TCP/UDP, socket C++, REST và gRPC

!!! abstract "🎯 Học xong bài này, bạn sẽ"
    - Nói được **địa chỉ IP**, **cổng**, **TCP** (như gọi điện: nối máy, nghe đủ, đúng thứ tự) khác **UDP** (như gửi bưu thiếp: không nối máy, mỗi tấm riêng, có thể mất) ở đâu, và chọn cái nào cho việc nào.
    - Viết và chạy được server + client TCP và UDP bằng socket POSIX trong **một chương trình C++** trên `127.0.0.1` (hai luồng), chọn cổng bằng `bind` cổng 0 rồi `getsockname`, đóng bằng RAII.
    - Giải thích và xử lý được ba lỗi kinh điển: `recv` trả ít hơn yêu cầu (TCP là dòng byte, không có ranh giới tin nhắn), `SIGPIPE`, `EADDRINUSE`.
    - Hiểu REST/HTTP là gì (có chạy `curl` thật trên máy), gRPC/protobuf ở mức ý tưởng, và biết dùng `ss`, `nc`, `curl -v`, `tcpdump` để gỡ lỗi mạng.

**Bạn cần biết trước:** [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md) (RAII, đóng tài nguyên trong hàm hủy), [Bài 11](../nhom-1-nen-tang-bo-nho/11-sao-chep-rule-of-3.md) và [Bài 12](../nhom-1-nen-tang-bo-nho/12-move-semantics.md) (vì sao lớp giữ tài nguyên cấm sao chép, cho di chuyển), [Bài 24](../nhom-3-da-luong/24-thread-co-ban.md) (`std::thread`, `join`).

## 🧠 Câu chuyện mở đầu

Muốn nói chuyện với bạn ở nhà khác, bạn có hai cách. Cách một là **gọi điện thoại**: quay số, chờ bạn nhấc máy, rồi cả hai nói qua lại; lời nào bạn nói, bạn nghe đúng thứ tự, và nếu đứt đường dây thì cả hai biết ngay. Cách hai là **gửi bưu thiếp**: bạn viết địa chỉ, bỏ vào hòm thư, không biết bạn đã nhận chưa, thư đến sau thư đi trước cũng chưa chắc.

Mạng máy tính có đúng hai kiểu đó. **TCP** là gọi điện, **UDP** là bưu thiếp. **Địa chỉ IP** là số nhà, **cổng** (port) là số phòng trong nhà đó: một máy chạy nhiều chương trình, cổng cho biết thư phải giao cho chương trình nào.

!!! info "Chỗ nào ví von không còn đúng?"
    Điện thoại có tiếng nói liên tục, còn TCP là một dòng **byte** mà bạn đọc từng khúc, và khúc nghe được **không nhất thiết khớp** với khúc người kia nói (mục 4). Bưu thiếp đến nguyên tấm hoặc không đến, còn UDP cũng vậy: mỗi gói đến nguyên vẹn hoặc mất hẳn. Ví von chỉ dùng ở đoạn mở đầu.

## 📖 Giải thích

### 1. Địa chỉ, cổng và vòng lặp nội bộ

**Địa chỉ IP** (IPv4) là bốn số từ 0 đến 255, như `192.168.1.5`. **Cổng** là số từ 0 đến 65535; chương trình "mở cổng" để nhận thư. Cặp `địa chỉ:cổng` xác định một đầu nối.

Địa chỉ `127.0.0.1` là **loopback**: mọi gói gửi tới đó quay lại chính máy bạn, không ra ngoài. Cả bài này chỉ dùng `127.0.0.1`, nên chương trình chạy an toàn, không cần mạng. Máy chủ web chuẩn nằm ở cổng 80 (HTTP) hay 443 (HTTPS); cổng nhỏ dưới 1024 thường cần quyền đặc biệt, nên ta để hệ điều hành chọn (mục 3).

### 2. TCP và UDP

| | TCP | UDP |
|---|---|---|
| Hình dung | Gọi điện | Bưu thiếp |
| Nối máy trước | Có (`connect`/`accept`) | Không |
| Đến đủ, đúng thứ tự | Có (mất thì tự gửi lại) | Không hứa: có thể mất, trùng, đảo |
| Đơn vị dữ liệu | Dòng byte, **không có ranh giới** | Gói (datagram), mỗi gói riêng |
| Chi phí | Cao hơn (nối máy, báo nhận) | Thấp |
| Hợp với | Web, file, cơ sở dữ liệu, mọi thứ cần đủ | Video/âm thanh trực tiếp, DNS, trò chơi (mất một ít không sao) |

Mất một gói là hỏng việc thì dùng TCP; gói cũ thành vô dụng (khung hình đã qua) và cần độ trễ thấp thì UDP.

### 3. Socket POSIX: một "cổng giao tiếp" là một số nguyên

**Socket** là đối tượng của hệ điều hành đại diện cho một đầu nối mạng. Trên Linux nó được cấp dưới dạng **file descriptor** (fd, một số `int`), giống file: dùng xong phải `close`. Đây là lý do ta bọc nó trong lớp RAII `Fd` (Ví dụ 1) y như ở [Bài 08](../nhom-1-nen-tang-bo-nho/08-raii.md): hàm hủy `close`, cấm sao chép (hai đối tượng cùng đóng một fd là lỗi), cho di chuyển.

Server TCP đi theo thứ tự: `socket` (tạo) → `bind` (gắn vào `địa chỉ:cổng`) → `listen` (bắt đầu nhận kết nối, hàng đợi cho các kết nối đến sớm) → `accept` (chờ một khách, trả về **một fd mới** riêng cho khách đó) → `recv`/`send` → `close`. Client chỉ cần `socket` → `connect` → `send`/`recv` → `close`. Vì `listen` đã có hàng đợi, client gọi `connect` trước khi server kịp `accept` vẫn ổn.

Số trong gói mạng theo **thứ tự byte mạng** (big-endian, byte lớn đứng trước); máy bạn có thể khác. `htons`/`htonl` đổi sang thứ tự mạng khi gửi, `ntohs`/`ntohl` đổi ngược khi nhận. Quên chúng thì cổng 8080 thành một số lạ.

Chọn cứng một cổng (như 8080) dễ **đụng** chương trình khác. Cách chắc ăn: `bind` vào cổng **0**, hệ điều hành chọn một cổng rảnh, rồi `getsockname` hỏi lại "mình được cấp cổng nào" (Ví dụ 1). Bài chỉ in "cổng > 0" vì số đó đổi mỗi lần chạy.

### 4. TCP là dòng byte: `recv` có thể trả ít hơn bạn xin

Gọi `recv(fd, buf, 100, 0)` nghĩa là "cho tôi **tối đa** 100 byte". Nó trả về số byte nhận được ngay lúc đó, có thể chỉ 1; trả `0` nghĩa là bên kia đã đóng (hết dữ liệu); trả `-1` là lỗi. TCP không nhớ "người kia gửi ba lần": ba lần `send` có thể dồn thành một lần `recv`, hoặc một lần `send` bị cắt thành nhiều lần `recv`.

Hệ quả: bạn phải **tự vạch ranh giới**. Hai cách thông dụng: kết thúc mỗi tin bằng ký tự đặc biệt (như `\n`, Ví dụ 1) hoặc gắn **tiền tố độ dài** (4 byte ghi độ dài, rồi đến nội dung, Ví dụ 2). Và phải **lặp** cho đến khi đủ số byte cần (hàm `nhan_du`). Phía gửi cũng vậy: `send` có thể gửi ít hơn xin, nên có hàm `gui_het`.

### 5. UDP: mỗi gói riêng, nhưng không hứa gì

Với UDP không có `connect/accept`: `sendto` gửi một gói tới `địa chỉ:cổng`, `recvfrom` nhận **một gói** (Ví dụ 3). Hai lần gửi `xin` và `chao` thành hai gói riêng, đọc ra hai lần, không dính vào nhau. Nhưng UDP **không bảo đảm** gói đến, đến một lần, hay đến đúng thứ tự; trên loopback ở ví dụ nhỏ hầu như luôn ổn, và đừng coi đó là lời hứa. Vì gói có thể không bao giờ đến, ví dụ đặt thời gian chờ `SO_RCVTIMEO`.

### 6. Ba lỗi kinh điển

**`EADDRINUSE`** ("địa chỉ đã dùng"): `bind` vào cổng đang có chương trình khác (hoặc chính bạn) giữ. Xử lý: chọn cổng khác, tắt chương trình kia (`ss -ltnp` cho biết ai giữ), hoặc dùng cổng 0. Server vừa tắt cũng có thể vướng trạng thái `TIME_WAIT` một lúc; `setsockopt(SO_REUSEADDR)` là cách thường dùng, nhưng mình **chưa chạy** tình huống đó trong bài này.

**`SIGPIPE`**: khi bạn `send` vào một kết nối mà bên kia đã đóng, hệ điều hành gửi tín hiệu `SIGPIPE` và **mặc định giết tiến trình** của bạn. Cách phòng: truyền cờ `MSG_NOSIGNAL` cho `send` (Linux), hoặc gọi `signal(SIGPIPE, SIG_IGN)` một lần ở đầu chương trình; khi đó `send` chỉ trả `-1` với `errno == EPIPE`.

Chú ý: lần `send` **đầu tiên** sau khi bên kia đóng thường vẫn "thành công" (dữ liệu chỉ vào bộ đệm); lỗi hiện ra ở lần sau, khi bên kia đã báo từ chối.

**`recv` ít hơn yêu cầu / dính tin**: mục 4. Đây là lỗi phổ biến nhất của người mới, vì thử nghiệm nhỏ trên máy mình luôn "tình cờ" khớp.

### 7. HTTP và REST

**HTTP** là giao thức dạng chữ chạy trên TCP: client gửi một **yêu cầu** gồm *phương thức* (`GET` lấy, `POST` gửi dữ liệu, `PUT`, `DELETE`), *đường dẫn* và các *header*; server trả **phản hồi** gồm *mã trạng thái* (200 thành công, 404 không thấy, 500 lỗi server), header và thân. **REST** là cách đặt tên: mỗi thứ là một *tài nguyên* có đường dẫn (`/ten.json`), và phương thức nói muốn làm gì với nó. Thân thường là JSON.

`curl` là công cụ dòng lệnh làm client HTTP; `curl -v` in cả yêu cầu lẫn phản hồi (Ví dụ 5 chạy thật trên localhost). Bạn không phải tự viết giao thức này bằng socket: dùng thư viện HTTP có sẵn.

### 8. gRPC và protobuf (chỉ nêu ý)

**gRPC** là khung gọi hàm từ xa: bạn mô tả dịch vụ và kiểu dữ liệu trong file `.proto` (ngôn ngữ **protobuf**), một công cụ sinh mã cho C++, Go và nhiều ngôn ngữ khác, rồi gọi hàm trên máy A là chạy hàm tương ứng trên máy B. Dữ liệu đi dạng nhị phân gọn, trên HTTP/2: kiểu chặt, nhanh, nhưng khó đọc bằng mắt và `curl` hơn REST+JSON. **Mình chưa cài và chưa chạy gRPC**, nên chỉ nêu ý.

### 9. Gỡ lỗi mạng: bộ công cụ

| Công cụ | Dùng để | Đã chạy? |
|---|---|---|
| `ss -ltn` (thêm `p` để xem tiến trình) | Liệt kê cổng đang **nghe** và ai giữ | Có (Ví dụ 5) |
| `nc` (netcat) | Làm client/server TCP thô: `nc -l` nghe, `nc host cổng` nối; `nc -z` thử cổng mở không | Có (Ví dụ 5) |
| `curl -v` | Xem yêu cầu và phản hồi HTTP | Có (Ví dụ 5) |
| `tcpdump -i lo` | Bắt từng gói đi qua card mạng | **Chưa chạy**: máy mình không đủ quyền |

Hỏi theo thứ tự: server có nghe không (`ss`)? Nối được không (`nc -z`)? Lời qua lại đúng không (`curl -v`, `tcpdump`)?

## 💻 Ví dụ code

Mọi ví dụ biên dịch bằng `g++ -std=c++17 -Wall -pthread`, chỉ dùng `127.0.0.1`, chạy kèm ASan + UBSan sạch. Trong mỗi ví dụ, **server chạy ở một `std::thread`, client ở luồng chính**. Nếu bạn thấy chữ `::` đứng trước tên hàm (`::socket`, `::close`), đó chỉ là cách gọi hàm toàn cục của hệ điều hành, tránh nhầm với hàm cùng tên khác.

### Ví dụ 1: Echo TCP và RAII cho fd

Lớp `Fd` giữ fd và `close` trong hàm hủy (1). `lang_nghe` bind cổng 0 (3) rồi hỏi lại cổng bằng `getsockname` (4). Server đọc **một dòng** (5): đọc từng byte tới `\n`. Client cố ý gửi `xin chao` bằng **hai** lần `send` (9) để thấy server vẫn ghép được.

```cpp
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

class Fd {                                                           // (1)
public:
    explicit Fd(int fd = -1) : fd_(fd) {}
    ~Fd() { if (fd_ >= 0) ::close(fd_); }
    Fd(const Fd&) = delete;
    Fd& operator=(const Fd&) = delete;
    Fd(Fd&& o) noexcept : fd_(o.fd_) { o.fd_ = -1; }
    int get() const { return fd_; }
private:
    int fd_;
};

Fd lang_nghe(std::uint16_t& port) {                                  // (2)
    Fd s(::socket(AF_INET, SOCK_STREAM, 0));
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);                      // 127.0.0.1
    a.sin_port = htons(0);                                           // (3)
    if (::bind(s.get(), reinterpret_cast<sockaddr*>(&a), sizeof a) < 0) std::perror("bind");
    if (::listen(s.get(), 8) < 0) std::perror("listen");
    socklen_t len = sizeof a;
    ::getsockname(s.get(), reinterpret_cast<sockaddr*>(&a), &len);   // (4)
    port = ntohs(a.sin_port);
    return s;
}

std::string doc_dong(int fd) {                                       // (5)
    std::string dong;
    char c;
    while (::recv(fd, &c, 1, 0) == 1) {
        dong += c;
        if (c == '\n') break;
    }
    return dong;
}

int main() {
    std::uint16_t port = 0;
    Fd nghe = lang_nghe(port);
    std::cout << "cong duoc cap > 0: " << (port > 0 ? "dung" : "sai") << "\n";

    std::thread may_chu([&nghe] {                                    // (6)
        Fd khach(::accept(nghe.get(), nullptr, nullptr));            // (7)
        std::string dong = doc_dong(khach.get());
        std::string tra = "echo: " + dong;
        ::send(khach.get(), tra.data(), tra.size(), 0);              // (8)
    });

    Fd c(::socket(AF_INET, SOCK_STREAM, 0));
    sockaddr_in dich{};
    dich.sin_family = AF_INET;
    dich.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    dich.sin_port = htons(port);
    if (::connect(c.get(), reinterpret_cast<sockaddr*>(&dich), sizeof dich) < 0) std::perror("connect");
    ::send(c.get(), "xin ", 4, 0);                                   // (9)
    ::send(c.get(), "chao\n", 5, 0);
    std::cout << doc_dong(c.get());
    may_chu.join();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | `Fd` sở hữu một fd, cấm sao chép, cho di chuyển | `~Fd` luôn `close` một lần |
| (2), (3) | Tạo socket nghe ở `127.0.0.1`, cổng 0 | hệ điều hành chưa chọn cổng |
| (4) | `getsockname` ghi cổng thật vào `a` | `port` > 0 |
| (6), (7) | Luồng server chờ ở `accept`; khi khách đến nhận về `khach` (fd mới) | `nghe` vẫn mở, `khach` là fd riêng |
| (9) | Client gửi `xin ` rồi `chao\n` | hai lần `send`, một dòng |
| (5) | Server đọc từng byte tới `\n`, ghép đủ `xin chao\n` | `dong` = `xin chao\n` |
| (8) | Server gửi lại `echo: ` + dòng; client đọc dòng đó và in | `join`, các `Fd` tự `close` |

**Kết quả khi chạy:**

```text
cong duoc cap > 0: dung
echo: xin chao
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0. Chú ý: ta không in số cổng vì nó thay đổi mỗi lần chạy. Cũng nhờ `listen` đã có hàng đợi, client `connect` được ngay cả khi luồng server chưa kịp tới `accept`.

### Ví dụ 2: Dòng byte dính tin, và tiền tố độ dài

Server nhận hai kết nối liên tiếp. Kết nối 1: client gửi `xin`, `chao`, `ban` bằng ba lần `gui_het` (6), server đọc bằng `recv` buffer 100 byte trong vòng lặp (5) cho tới khi bên kia đóng. Kết nối 2: cũng ba tin nhưng qua `gui_tin` (7), có **tiền tố 4 byte độ dài** (3), và server dùng `nhan_tin` (4).

```cpp
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <iostream>
#include <string>
#include <thread>

class Fd {
public:
    explicit Fd(int fd = -1) : fd_(fd) {}
    ~Fd() { if (fd_ >= 0) ::close(fd_); }
    Fd(const Fd&) = delete;
    Fd& operator=(const Fd&) = delete;
    int get() const { return fd_; }
private:
    int fd_;
};

sockaddr_in loopback(std::uint16_t port) {
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons(port);
    return a;
}

bool gui_het(int fd, const char* p, std::size_t n) {                 // (1)
    while (n > 0) {
        ssize_t k = ::send(fd, p, n, MSG_NOSIGNAL);
        if (k <= 0) return false;
        p += k;
        n -= static_cast<std::size_t>(k);
    }
    return true;
}
bool nhan_du(int fd, char* p, std::size_t n) {                       // (2)
    while (n > 0) {
        ssize_t k = ::recv(fd, p, n, 0);
        if (k <= 0) return false;                                    // 0 = ben kia da dong
        p += k;
        n -= static_cast<std::size_t>(k);
    }
    return true;
}
bool gui_tin(int fd, const std::string& s) {                         // (3)
    std::uint32_t dai = htonl(static_cast<std::uint32_t>(s.size()));
    return gui_het(fd, reinterpret_cast<const char*>(&dai), 4) && gui_het(fd, s.data(), s.size());
}
bool nhan_tin(int fd, std::string& s) {                              // (4)
    std::uint32_t dai = 0;
    if (!nhan_du(fd, reinterpret_cast<char*>(&dai), 4)) return false;
    s.assign(ntohl(dai), '\0');
    return nhan_du(fd, &s[0], s.size());
}

int main() {
    Fd nghe(::socket(AF_INET, SOCK_STREAM, 0));
    sockaddr_in a = loopback(0);
    ::bind(nghe.get(), reinterpret_cast<sockaddr*>(&a), sizeof a);
    ::listen(nghe.get(), 8);
    socklen_t len = sizeof a;
    ::getsockname(nghe.get(), reinterpret_cast<sockaddr*>(&a), &len);
    std::uint16_t port = ntohs(a.sin_port);

    std::thread may_chu([&nghe] {
        {   // ket noi 1: doc tho cho den khi ben kia dong
            Fd k(::accept(nghe.get(), nullptr, nullptr));
            std::string tong;
            char buf[100];
            int so_lan = 0;
            ssize_t n;
            while ((n = ::recv(k.get(), buf, sizeof buf, 0)) > 0) {  // (5)
                tong.append(buf, static_cast<std::size_t>(n));
                ++so_lan;
            }
            std::cout << "tho: " << tong.size() << " byte, noi dung \"" << tong << "\"\n";
            std::cout << "tho: so lan recv >= 1 va <= 3: " << (so_lan >= 1 && so_lan <= 3 ? "dung" : "sai") << "\n";
        }
        {   // ket noi 2: co tien to do dai
            Fd k(::accept(nghe.get(), nullptr, nullptr));
            std::string tin;
            while (nhan_tin(k.get(), tin)) std::cout << "tin: \"" << tin << "\"\n";
        }
    });

    for (int lan = 0; lan < 2; ++lan) {
        Fd c(::socket(AF_INET, SOCK_STREAM, 0));
        sockaddr_in d = loopback(port);
        ::connect(c.get(), reinterpret_cast<sockaddr*>(&d), sizeof d);
        if (lan == 0) {
            gui_het(c.get(), "xin", 3);                              // (6)
            gui_het(c.get(), "chao", 4);
            gui_het(c.get(), "ban", 3);
        } else {
            gui_tin(c.get(), "xin");                                 // (7)
            gui_tin(c.get(), "chao");
            gui_tin(c.get(), "ban");
        }
    }                                                                // (8)
    may_chu.join();
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1), (2) | Gửi hết / nhận đủ `n` byte bằng vòng lặp; `recv` trả `<= 0` thì thất bại | `p` tiến lên, `n` giảm tới 0 |
| (3), (4) | Gửi 4 byte độ dài (đã `htonl`) rồi nội dung; nhận ngược lại | một tin = một lần `nhan_tin` |
| (6) | Kết nối 1: ba lần gửi `xin`, `chao`, `ban` | 10 byte, ba lần `send` |
| (5) | `recv` lặp tới khi trả 0 (bên kia đóng) | `tong` = `xinchaoban` |
| (7) | Kết nối 2: ba tin có tiền tố | `tin` lần lượt `xin`, `chao`, `ban` |
| (8) | Vòng lặp kết thúc, `Fd c` đóng, server thấy EOF | `nhan_tin` trả `false`, server thoát |

**Kết quả khi chạy:**

```text
tho: 10 byte, noi dung "xinchaoban"
tho: so lan recv >= 1 va <= 3: dung
tin: "xin"
tin: "chao"
tin: "ban"
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0, và lặp 5 lần cho đúng cùng đầu ra. Tổng byte và nội dung của kết nối 1 luôn như vậy, nhưng **số lần `recv` thì không**: có thể 1, 2 hoặc 3 tùy thời điểm, nên mình chỉ in "trong khoảng 1 đến 3". Đó là điều TCP cho bạn: một dòng byte, không biết bạn đã gửi mấy lần.

Hai cách vạch ranh giới tin nhắn đã thấy: ký tự kết thúc (Ví dụ 1) và tiền tố độ dài (Ví dụ 2).

### Ví dụ 3: UDP, mỗi gói một lần nhận

`SOCK_DGRAM` (1) là UDP. Bên nhận `bind` cổng 0 (2) và đặt thời gian chờ 2 giây (3) để không treo mãi. Bên gửi dùng `sendto` (4) hai lần, bên nhận `recvfrom` (5) hai lần.

```cpp
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#include <cstdint>
#include <iostream>
#include <string>

class Fd {
public:
    explicit Fd(int fd = -1) : fd_(fd) {}
    ~Fd() { if (fd_ >= 0) ::close(fd_); }
    Fd(const Fd&) = delete;
    Fd& operator=(const Fd&) = delete;
    int get() const { return fd_; }
private:
    int fd_;
};

int main() {
    Fd nhan(::socket(AF_INET, SOCK_DGRAM, 0));                       // (1)
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons(0);
    ::bind(nhan.get(), reinterpret_cast<sockaddr*>(&a), sizeof a);   // (2)
    socklen_t len = sizeof a;
    ::getsockname(nhan.get(), reinterpret_cast<sockaddr*>(&a), &len);

    timeval han{2, 0};                                               // (3)
    ::setsockopt(nhan.get(), SOL_SOCKET, SO_RCVTIMEO, &han, sizeof han);

    Fd gui(::socket(AF_INET, SOCK_DGRAM, 0));
    ::sendto(gui.get(), "xin", 3, 0, reinterpret_cast<sockaddr*>(&a), sizeof a);    // (4)
    ::sendto(gui.get(), "chao", 4, 0, reinterpret_cast<sockaddr*>(&a), sizeof a);

    for (int i = 0; i < 2; ++i) {
        char buf[100];
        ssize_t n = ::recvfrom(nhan.get(), buf, sizeof buf, 0, nullptr, nullptr);   // (5)
        if (n < 0) { std::cout << "het gio cho\n"; break; }
        std::cout << "goi " << i + 1 << ": " << n << " byte \"" << std::string(buf, static_cast<std::size_t>(n)) << "\"\n";
    }
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1), (2) | Socket UDP, bind `127.0.0.1` cổng 0, rồi `getsockname` lấy cổng thật | `a` chứa địa chỉ nhận |
| (3) | `recvfrom` chờ tối đa 2 giây | không treo vô hạn |
| (4) | Hai gói: `xin` (3 byte) và `chao` (4 byte) | hai gói riêng trong hàng đợi nhận |
| (5) | Mỗi `recvfrom` lấy đúng **một** gói | gói 1 rồi gói 2 |

**Kết quả khi chạy:**

```text
goi 1: 3 byte "xin"
goi 2: 4 byte "chao"
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0, lặp 3 lần cho cùng đầu ra. So với Ví dụ 2: ở TCP, `xin` và `chao` có thể dính thành `xinchao`; ở UDP chúng luôn là hai gói. Nhưng trên mạng thật UDP có thể làm mất hay đảo thứ tự; ở đây chạy trên loopback với hai gói nhỏ nên luôn đủ.

### Ví dụ 4: `EADDRINUSE` và `EPIPE`

Phần 1: `bind` hai socket vào cùng một cổng, lần hai thất bại (1); ta lưu `errno` ngay (2) vì lời gọi khác có thể ghi đè nó. Phần 2: server đóng kết nối ngay (3); client `send` đều đặn với `MSG_NOSIGNAL` (4) cho tới khi lỗi.

```cpp
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <thread>

class Fd {
public:
    explicit Fd(int fd = -1) : fd_(fd) {}
    ~Fd() { if (fd_ >= 0) ::close(fd_); }
    Fd(const Fd&) = delete;
    Fd& operator=(const Fd&) = delete;
    int get() const { return fd_; }
private:
    int fd_;
};

int main() {
    // --- Loi 1: EADDRINUSE ---
    Fd a1(::socket(AF_INET, SOCK_STREAM, 0));
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons(0);
    ::bind(a1.get(), reinterpret_cast<sockaddr*>(&a), sizeof a);
    ::listen(a1.get(), 8);
    socklen_t len = sizeof a;
    ::getsockname(a1.get(), reinterpret_cast<sockaddr*>(&a), &len);   // a.sin_port = cong dang bi chiem

    Fd a2(::socket(AF_INET, SOCK_STREAM, 0));
    int r = ::bind(a2.get(), reinterpret_cast<sockaddr*>(&a), sizeof a);   // (1)
    int e = errno;                                                   // (2)
    std::cout << "bind lan 2: " << r << ", errno la EADDRINUSE: " << (e == EADDRINUSE ? "dung" : "sai")
              << ", thong bao: " << std::strerror(e) << "\n";

    // --- Loi 2: ghi vao ket noi ma ben kia da dong ---
    Fd c(::socket(AF_INET, SOCK_STREAM, 0));
    ::connect(c.get(), reinterpret_cast<sockaddr*>(&a), sizeof a);
    {
        Fd k(::accept(a1.get(), nullptr, nullptr));
    }                                                                // (3)
    int lan_thanh_cong = 0;
    for (int i = 0; i < 100; ++i) {
        ssize_t n = ::send(c.get(), "x", 1, MSG_NOSIGNAL);           // (4)
        if (n < 0) {
            int loi = errno;
            std::cout << "send lan " << (i >= 1 ? "sau" : "dau") << " that bai, errno la EPIPE: "
                      << (loi == EPIPE ? "dung" : "sai") << "\n";
            break;
        }
        ++lan_thanh_cong;
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    std::cout << "co it nhat 1 lan gui 'thanh cong' truoc khi bao loi: " << (lan_thanh_cong >= 1 ? "dung" : "sai") << "\n";
    return 0;
}
```

| Dòng | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | Cổng đang nghe bởi `a1`, `bind` lần hai trả -1 | `a2` không dùng được |
| (2) | `errno` là `EADDRINUSE`; `strerror` cho dòng chữ người đọc được | `e` giữ mã lỗi |
| (3) | Khối `{}` kết thúc: `k` đóng | bên server đã đóng, client chưa biết |
| (4) | Các `send` đầu vào bộ đệm; sau khi bên kia từ chối thì trả -1, `errno` = `EPIPE` | không bị giết nhờ `MSG_NOSIGNAL` |

**Kết quả khi chạy:**

```text
bind lan 2: -1, errno la EADDRINUSE: dung, thong bao: Address already in use
send lan sau that bai, errno la EPIPE: dung
co it nhat 1 lan gui 'thanh cong' truoc khi bao loi: dung
```

Mình chạy với ASan + UBSan: sạch, mã thoát 0, lặp 5 lần cho cùng đầu ra. Dòng cuối chứng minh điều ở mục 6: có ít nhất một lần `send` "thành công" **sau khi** bên kia đã đóng. **Thử thay đổi** (đã chạy):

- Đổi `MSG_NOSIGNAL` thành `0` (đoạn dưới là phần đổi). Biên dịch vẫn sạch, nhưng chương trình **bị hệ điều hành giết** ở lần `send` lỗi: shell báo mã thoát **141** (128 cộng tín hiệu số 13, `SIGPIPE`). Các dòng `cout` đã in trước đó cũng **không hiện** trong lần mình chạy, vì đầu ra bị đệm (stdout là ống) và tiến trình chết trước khi xả.

### Ví dụ 5: HTTP/REST, `ss` và `nc` trên localhost

Phần này là lệnh shell, không phải C++. Ta dùng máy chủ HTTP thử của Python (cổng 0 để hệ điều hành chọn; dòng đầu của nó in ra cổng thật), thư mục có một file `ten.json`. Trong kết quả mình thay số cổng bằng `PORT`.

```bash
python3 -u -m http.server 0 --bind 127.0.0.1 &       # (1) in "Serving HTTP on 127.0.0.1 port NNNNN"
curl -sv http://127.0.0.1:PORT/ten.json              # (2)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:PORT/khong-co          # (3)
curl -s -o /dev/null -w "%{http_code}\n" -X POST -d '{}' http://127.0.0.1:PORT/ten.json   # (4)
ss -ltnp | grep PORT                                 # (5)

nc -l 127.0.0.1 PORT2 > nhan.txt &                   # (6)
echo "xin chao nc" | nc -N 127.0.0.1 PORT2           # (7)
cat nhan.txt
nc -z 127.0.0.1 PORT2; echo "ma thoat=$?"            # (8)
```

| Lệnh | Chuyện gì xảy ra | Trạng thái lúc này |
|---|---|---|
| (1) | Server HTTP nghe `127.0.0.1`, cổng do hệ điều hành chọn | một tiến trình nghe |
| (2) | `GET /ten.json`: in yêu cầu (`>`) và phản hồi (`<`) | mã `200`, thân JSON 13 byte |
| (3) | Đường dẫn không tồn tại | mã `404` |
| (4) | `POST` tới máy chủ chỉ biết `GET` | mã `501` (không hỗ trợ) |
| (5) | `ss` cho thấy `LISTEN` ở `127.0.0.1:PORT` và tiến trình giữ | cột `users:` có `python3` |
| (6), (7) | `nc` nghe rồi nhận một dòng từ `nc` client | `nhan.txt` = `xin chao nc` |
| (8) | Sau khi server `nc` thoát, không còn ai nghe | `nc -z` trả mã thoát 1 |

**Kết quả khi chạy (rút gọn; cổng thay bằng `PORT`, ngày giờ và phiên bản đổi theo máy):**

```text
> GET /ten.json HTTP/1.1
> Host: 127.0.0.1:PORT
> User-Agent: curl/8.5.0
> Accept: */*
< HTTP/1.0 200 OK
< Content-type: application/json
< Content-Length: 13
{"ten":"an"}
404
501
LISTEN 0      5          127.0.0.1:PORT      0.0.0.0:*    users:(("python3",pid=N,fd=N))
xin chao nc
ma thoat=1
```

Mình chạy thật. Hai điều đáng nhớ: máy chủ này nói HTTP/1.0 và chỉ cài `GET`, còn REST thật thường dùng đủ phương thức; mã `404`/`501` là cách server trả lời "không thấy"/"không hỗ trợ" mà không cần xem thân. **`tcpdump -i lo` mình có thử** nhưng bị từ chối (`You don't have permission to perform this capture`, máy không cấp quyền), nên **mình chưa chạy** được `tcpdump` và không dán kết quả của nó.

## Go: `net.Listen`, `net.Dial` và ranh giới tương tự

!!! info "Bạn biết Go?"
    Mình đã chạy một chương trình Go 1.22.2 nhỏ (`go vet` sạch) để kiểm các ý dưới đây.
    - **Cùng khái niệm, API gọn hơn**: `net.Listen("tcp", "127.0.0.1:0")` gộp `socket`+`bind`+`listen`, và `ln.Addr()` cho cổng thật (mình in `true` cho "cổng > 0"); `ln.Accept()` và `net.Dial(...)` tương ứng `accept` và `connect`. Go **không** bắt bạn `close` bằng tay theo kiểu RAII; bạn dùng `defer c.Close()`.
    - **Cạm bẫy giống hệt**: `c.Read(buf)` trong Go cũng có thể trả ít hơn `len(buf)`. Trong lần chạy của mình (server ghi `xin`, nghỉ 50 ms, rồi ghi `chao`), `Read` đầu tiên trả ít hơn 7 byte, và `io.ReadFull(c, buf[n:])` đọc nốt cho đủ (tương đương `nhan_du`). Con số chính xác phụ thuộc thời điểm, nên đừng dựa vào nó.
    - **`SIGPIPE` không giết bạn**: ghi vào kết nối đã bị đóng, `Write` trả lỗi có thể kiểm bằng `errors.Is(err, syscall.EPIPE)` (mình in `true`) và tiến trình vẫn sống. Bind lần hai vào cổng đang dùng cho `errors.Is(err, syscall.EADDRINUSE)` đúng (mình in `true`). Đó là cùng hai lỗi của Ví dụ 4, khác ở chỗ Go xử lý `SIGPIPE` giúp bạn.
    - **HTTP**: `net/http` có sẵn trong thư viện chuẩn Go nên ít khi viết socket trực tiếp; mình **chưa chạy** `net/http` hay gRPC cho Go.

## 🎤 Câu hỏi phỏng vấn hay gặp

??? question "TCP khác UDP thế nào? Khi nào dùng cái nào?"
    TCP: hướng kết nối, tin cậy (mất thì gửi lại), đúng thứ tự, là dòng byte không ranh giới; chi phí cao hơn. UDP: không kết nối, không bảo đảm đến/đúng thứ tự, mỗi gói là một đơn vị riêng; nhẹ, độ trễ thấp. Cần đủ và đúng (file, web, cơ sở dữ liệu) thì TCP; cần nhanh và mất một ít không sao (video trực tiếp, trò chơi, DNS) thì UDP.

??? question "Vì sao `recv` trả ít byte hơn yêu cầu? Xử lý thế nào?"
    TCP là dòng byte, không giữ ranh giới giữa các lần `send`; `recv` trả những gì đang có ngay (tối đa số xin). Phải lặp tới khi đủ số byte cần và tự vạch ranh giới tin (ký tự kết thúc hoặc tiền tố độ dài). `recv` trả 0 là bên kia đã đóng, trả -1 là lỗi.

??? question "`SIGPIPE` là gì? Tránh thế nào?"
    Tín hiệu hệ điều hành gửi khi bạn ghi vào kết nối mà bên kia đã đóng; mặc định nó kết thúc tiến trình (mình chạy: mã thoát 141). Tránh bằng `MSG_NOSIGNAL` ở `send` hoặc `signal(SIGPIPE, SIG_IGN)`, rồi kiểm `errno == EPIPE`. Lần `send` đầu sau khi bên kia đóng thường vẫn "thành công".

??? question "REST là gì? GET khác POST thế nào? 404 và 500 nghĩa là gì?"
    REST: cách thiết kế API HTTP theo *tài nguyên* (mỗi thứ có đường dẫn) và *phương thức* (`GET` lấy, `POST` tạo/gửi dữ liệu, `PUT` thay, `DELETE` xóa). `GET` chỉ đọc, không nên đổi trạng thái. `404`: không có tài nguyên đó. `500`: server gặp lỗi nội bộ.

??? question "Mạng không thông, bạn gỡ lỗi từ đâu?"
    `ss -ltnp` xem server có nghe cổng không; `nc -z host cổng` hoặc `nc host cổng` xem nối được không; `curl -v` xem trao đổi HTTP; `tcpdump` xem tận gói khi cần (cần quyền; mình chưa chạy). Đi từ gần (có nghe không) đến xa (gói đi thế nào).

## ⚠️ Lỗi thường gặp

!!! warning "Lỗi 1: Giả định một `send` ứng với một `recv`"
    Thử nghiệm nhỏ trên cùng máy thường khớp, rồi sai lúc triển khai thật vì TCP không giữ ranh giới. Luôn lặp `recv` cho đủ và tự vạch ranh giới tin (Ví dụ 2). Cũng đừng quên `send` có thể gửi ít hơn xin.

!!! warning "Lỗi 2: Quên đóng fd, hoặc để `SIGPIPE` giết server"
    Không `close` fd thì rò rỉ cho tới khi hết số fd cho phép; dùng RAII `Fd` để mọi đường thoát đều đóng. Server không chặn `SIGPIPE` có thể chết vì một khách bỏ đi giữa chừng; luôn `MSG_NOSIGNAL` hoặc `SIG_IGN`, và kiểm giá trị `send` trả về.

## ✍️ Trắc nghiệm

<div class="quiz" data-bai="44" markdown>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 1.** Client gửi `"ab"` rồi `"cd"` bằng hai lần `send` trên một kết nối TCP. Server chạy đoạn sau. Điều nào chắc chắn đúng?

```text
char buf[100];
ssize_t n;
std::string tong;
while ((n = recv(fd, buf, sizeof buf, 0)) > 0) tong.append(buf, n);
// sau khi vòng lặp kết thúc
```

- `recv` đầu tiên luôn trả đúng 2 byte, `ab`
- `tong` có thể là `cd` vì tin gửi sau ghi đè tin gửi trước
- `tong` là `abcd`, nhưng số lần `recv` đã gọi thì không chắc là 2
- Vòng lặp không kết thúc vì `recv` chặn mãi

<p class="giai-thich" markdown>Vòng lặp chỉ dừng khi `recv` trả 0 (bên kia đóng) hoặc lỗi; tới lúc đó đã nhận hết, nên `tong` là `abcd`. Số lần `recv` thì tùy thời điểm: hai lần `send` có thể gộp vào một lần nhận hay bị chia khác đi, đó là hệ quả của dòng byte không có ranh giới. Vì thế `recv` đầu không nhất thiết trả 2 byte. Dữ liệu đến sau được nối vào sau, không ghi đè. Và vòng lặp kết thúc khi bên kia đóng kết nối, nên không chặn mãi nếu client đã đóng.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 2.** Bạn viết chương trình truyền một file sao lưu 2 GB giữa hai máy, mất một byte là file hỏng. Nên dùng gì?

- TCP, vì nó gửi lại gói mất và giữ đúng thứ tự
- UDP, vì nhẹ hơn nên truyền xong nhanh hơn
- UDP, vì mỗi gói giữ nguyên ranh giới nên không cần ghép
- Cả hai như nhau, vì mạng nội bộ không bao giờ mất gói

<p class="giai-thich" markdown>Khi mất một byte là hỏng, ta cần sự tin cậy: TCP gửi lại phần mất và giữ đúng thứ tự, nên là lựa chọn mặc định ở đây. UDP nhẹ hơn thật, nhưng tự nó không bù phần mất nên bạn phải tự viết cơ chế gửi lại. Ranh giới của UDP không giúp gì cho việc bảo đảm đủ dữ liệu. Và mạng nội bộ vẫn có thể rớt gói khi quá tải, nên không thể giả định không bao giờ mất.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 3.** Đọc đoạn sau. `a.sin_port` được đặt thành `htons(0)` rồi gọi `bind`. Hàm in ra gì?

```text
sockaddr_in a{};
a.sin_family = AF_INET;
a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
a.sin_port = htons(0);
bind(fd, (sockaddr*)&a, sizeof a);
std::cout << ntohs(a.sin_port) << "\n";
```

- Một cổng rảnh mà hệ điều hành đã chọn giúp bạn
- Lỗi chạy, vì cổng 0 không được phép dùng
- 65535, vì 0 được hiểu là cổng lớn nhất
- 0, vì `bind` không ghi cổng được cấp vào `a`

<p class="giai-thich" markdown>`bind` đọc `a` để biết cần gắn vào đâu, nhưng không ghi cổng được cấp ngược lại vào biến của bạn; `a` vẫn giữ 0. Muốn biết cổng thật phải gọi `getsockname` (Ví dụ 1). Cổng 0 hợp lệ và nghĩa là "hệ điều hành chọn giúp", nên không lỗi. 65535 là cổng lớn nhất, chẳng liên quan gì tới giá trị này.</p>
</div>

<div class="cau-hoi" data-dap-an="2" markdown>
**Câu 4.** `recv(fd, buf, 100, 0)` trả về `0`. Điều đó có nghĩa là gì?

- Bên kia chưa gửi gì và bạn nên gọi lại ngay
- Bên kia đã đóng chiều gửi, hết dữ liệu
- Có lỗi mạng, và bạn cần xem `errno`
- Bộ đệm `buf` quá nhỏ nên chưa nhận được byte nào

<p class="giai-thich" markdown>Với TCP, `recv` trả 0 báo hiệu bên kia đã đóng (hết dữ liệu), còn lỗi thì trả -1 kèm `errno`. Chưa có dữ liệu thì `recv` (chế độ chặn) đứng chờ chứ không trả 0. Và buffer nhỏ không gây ra 0: nó chỉ làm `recv` nhận ít hơn, phần còn lại ở lần sau.</p>
</div>

<div class="cau-hoi" data-dap-an="3" markdown>
**Câu 5.** Server đã chạy được vài giờ, bỗng chết ngay khi một khách bỏ đi giữa lúc server đang `send` cho khách đó. Log không có lỗi nào. Nguyên nhân hợp lý nhất?

- `send` ném ngoại lệ `std::runtime_error` không ai bắt
- Hết fd, nên `send` chết ngay lập tức
- Nhận `SIGPIPE` khi ghi vào kết nối đã đóng, và tín hiệu này mặc định giết tiến trình
- `accept` bị gọi hai lần cho cùng một khách

<p class="giai-thich" markdown>`send` vào kết nối bên kia đã đóng sinh `SIGPIPE` và hành động mặc định là kết thúc tiến trình, nên không có dòng log nào (mình chạy: mã thoát 141). Hàm `send` của POSIX là hàm C và không ném ngoại lệ. Hết fd thì lỗi hiện ra ở `socket` hay `accept` và trả -1 với `EMFILE`, không giết tiến trình. Gọi `accept` hai lần chỉ làm server đợi thêm một khách, không gây chết đột ngột.</p>
</div>

<div class="cau-hoi" data-dap-an="1" markdown>
**Câu 6.** Bạn chạy `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:PORT/khong-co` và nhận `404`. Điều này cho biết gì?

- Không có tài nguyên ở đường dẫn đó
- Server không chạy, hoặc đã từ chối kết nối của curl
- Server gặp lỗi bên trong khi đang xử lý yêu cầu
- Server không hỗ trợ phương thức `GET` của yêu cầu

<p class="giai-thich" markdown>`404` là "không thấy": server đã nhận và hiểu yêu cầu nhưng không có thứ ở đường dẫn đó (mình chạy ở Ví dụ 5). Server không chạy thì `curl` không có mã HTTP nào để in (nó báo lỗi kết nối), chứ không phải 404. Lỗi bên trong server là nhóm `5xx` như `500`. Không hỗ trợ phương thức là `501` hoặc `405`, như `POST` ở Ví dụ 5 nhận `501`.</p>
</div>

<div class="cau-hoi" data-dap-an="4" markdown>
**Câu 7.** Chương trình chạy lần hai báo `bind: Address already in use` dù bạn đã đóng cửa sổ chạy lần đầu. Việc nào hợp lý nhất để biết chuyện gì?

- Khởi động lại máy tính, vì lỗi này chỉ do hệ điều hành gây ra
- Thêm `sleep` trước `bind` cho đỡ va chạm
- Đổi `htons` thành `htonl` ở dòng gán cổng
- Chạy `ss -ltnp` xem tiến trình nào đang nghe cổng đó

<p class="giai-thich" markdown>`ss -ltnp` liệt kê cổng đang nghe cùng tiến trình giữ nó, nên có thể thấy bản chạy lần đầu vẫn còn sống ngầm; từ đó tắt nó hoặc đổi cổng (tốt hơn: bind cổng 0). Khởi động lại máy là cách quá nặng và không giải thích nguyên nhân. `sleep` không làm cổng rảnh nếu tiến trình kia còn sống. `htonl` dành cho số 32 bit, dùng cho cổng 16 bit là sai kiểu và không liên quan đến lỗi này.</p>
</div>

</div>

## 🔑 Tóm tắt

1. **IP:cổng** xác định một đầu nối; `127.0.0.1` là loopback (không ra ngoài). **TCP** (gọi điện): nối máy, đủ, đúng thứ tự, dòng byte không ranh giới; **UDP** (bưu thiếp): không nối, mỗi gói riêng, không hứa gì.
2. Socket POSIX là một **fd** nên bọc bằng RAII (`Fd`, cấm sao chép, đóng trong hàm hủy). Server: `socket` → `bind` → `listen` → `accept`; client: `socket` → `connect`. Chọn cổng bằng `bind` cổng 0 rồi `getsockname` (mình chạy: không va chạm, không cố định số).
3. **`recv` có thể trả ít hơn xin** và trả 0 khi bên kia đóng; phải lặp tới khi đủ và tự vạch ranh giới tin bằng ký tự kết thúc hoặc tiền tố độ dài (Ví dụ 2 chạy: ba lần `send` thành `xinchaoban`); UDP thì mỗi `recvfrom` là một gói (Ví dụ 3).
4. Lỗi kinh điển: `EADDRINUSE` (bind trùng cổng), `SIGPIPE` giết tiến trình khi ghi vào kết nối đã đóng (mình chạy: mã thoát 141; phòng bằng `MSG_NOSIGNAL`), và lần `send` đầu sau khi bên kia đóng vẫn có thể "thành công".
5. **HTTP/REST** là yêu cầu chữ (`GET`, `POST`, đường dẫn) và phản hồi có mã (200, 404, 500) mà `curl -v` cho xem (mình chạy trên localhost); **gRPC/protobuf** là gọi hàm từ xa nhị phân qua `.proto` (mình chưa chạy); gỡ lỗi bằng `ss`, `nc`, `curl -v` (đã chạy) và `tcpdump` (chưa chạy: không đủ quyền); Go có `net.Listen`/`net.Dial` cùng các cạm bẫy y hệt, riêng `SIGPIPE` thì Go xử lý giúp.
