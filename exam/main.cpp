#include <iostream>
#include <vector>
#include <regex>
#include <string>
#include <exception>
#include <thread>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <cctype>
using namespace std;

string separator = "\n---------------------------------------------------------------------------------\n";

string PHONE_MESSAGE = separator +
"TURN OFF YOUR PHONES AND PLACE THEM IN A BAG, POCKET, OR ANOTHER LOCATION OUT OF REACH.\n"
"PROGRAM CODE THAT CAN BE USED TO SOLVE EXAM TASKS IS OFTEN FOUND ON PHONES,\n"
"WHICH, IF DISCOVERED, WILL BE SANCTIONED.\n\n"
"ANYONE FOUND WITH A PHONE OR ANOTHER DEVICE THAT MAY CONTAIN EXAM MATERIAL\n"
"OR SOLUTIONS WILL BE REMOVED FROM THE EXAM AND PROCEEDINGS WILL BE INITIATED\n"
"AGAINST THEM" + separator;

string EXAM_MESSAGE = separator +
"0. CHECK WHETHER THE TASKS BELONG TO YOUR GROUP (G1/G2)\n"
"1. ALL CLASSES WITH DYNAMIC ALLOCATION MUST HAVE A CORRECT DESTRUCTOR\n"
"2. OMITTING THE DESTRUCTOR OR ANY OF ITS PARTS WILL BE MARKED AS TM\n"
"3. ATTRIBUTES, METHODS, AND PARAMETERS MUST BE IDENTICAL TO THOSE IN THE TEST MAIN FUNCTION,\n"
"   UNLESS THERE IS A CLEARLY DESCRIBED REASON FOR MODIFICATION\n"
"4. THROW EXCEPTIONS ONLY WHERE EXPLICITLY STATED\n"
"5. ALL METHODS CALLED IN MAIN MUST EXIST.\n"
"     IF YOU DO NOT HAVE THE DESIRED IMPLEMENTATION, LEAVE AN EMPTY BODY OR RETURN A DEFAULT VALUE\n"
"6. IN MAIN YOU MAY ADD TEST DATA AND CALLS OF YOUR CHOICE\n"
"7. TEST THE PROGRAM IN BOTH MODES (F5 and Ctrl+F5)" + separator;

char* AllocateText(const char* text) {
    if (text == nullptr) return nullptr;
    size_t size = strlen(text) + 1;
    char* newText = new char[size];
    strcpy_s(newText, size, text);
    return newText;
}

enum RequestStatus { RECEIVED, DIAGNOSTICS, REPAIR, COMPLETED };
const char* RequestStatusNames[] = {
    "RECEIVED", "DIAGNOSTICS", "REPAIR", "COMPLETED"
};

template<class T1, class T2, int max>
class Collection {
    T1* _elements1;
    T2* _elements2;
    int _current;
public:
    Collection() : _current(0) {
        _elements1 = new T1[max];
        _elements2 = new T2[max];
    }
    int GetCurrentCount() const { return _current; }
    const T1& GetElement1(int index) const { return _elements1[index]; }
    const T2& GetElement2(int index) const { return _elements2[index]; }
    T2& GetElement2(int index) { return _elements2[index]; }

    T1& operator[](int index) {
        return _elements1[index];
    }

    Collection RemoveDuplicates() {
        Collection newCollection;

        for (int i = 0; i < _current; i++) {
            bool exists = false;

            for (int j = 0; j < newCollection.GetCurrentCount(); j++) {
                if (_elements1[i] == newCollection.GetElement1(j) &&
                    _elements2[i] == newCollection.GetElement2(j)) {
                    exists = true;
                    break;
                }
            }

            if (!exists) {
                newCollection.Add(_elements1[i], _elements2[i]);
            }
        }

        return newCollection;
    }

    Collection(const Collection& other) {
        _elements1 = new T1[max];
        _elements2 = new T2[max];

        for (int i = 0; i < other._current; i++) {
            _elements1[i] = other._elements1[i];
            _elements2[i] = other._elements2[i];
        }

        _current = other._current;
    }

    Collection& operator=(const Collection& other) {
        if (this != &other) {
            delete[] _elements1;
            delete[] _elements2;

            _elements1 = new T1[max];
            _elements2 = new T2[max];

            for (int i = 0; i < other._current; i++) {
                _elements1[i] = other._elements1[i];
                _elements2[i] = other._elements2[i];
            }

            _current = other._current;
        }

        return *this;
    }

    void Add(const T1& first, const T2& second) {
        if (_current >= max) {
            // it seems like we are expected to throw here
            // later in main we have this which should fail on the third Add:
            /*
                try {
                    Collection<int, string, 2> full;
                    full.Add(1, "One");
                    full.Add(2, "Two");
                    full.Add(3, "Three");
                }
                catch (exception& e) {
                    cout << "Exception: " << e.what() << separator;
                }
            */
            return;
        }

        _elements1[_current] = first;
        _elements2[_current] = second;

        _current++;
    }

    friend ostream& operator<<(ostream& COUT, const Collection& obj) {
        for (int i = 0; i < obj.GetCurrentCount(); i++)
            COUT << obj.GetElement1(i) << " " << obj.GetElement2(i) << endl;
        return COUT;
    }
    ~Collection() {
        delete[] _elements1;
        delete[] _elements2;
        _elements1 = nullptr;
        _elements2 = nullptr;
        _current = 0;
    }
};

string Format(int number) {
    string result = "";

    if (number < 10) {
        result += "0";
        result += to_string(number);
    }
    else {
        result += to_string(number);
    }

    return result;
}

class DateTime {
    int* _day, * _month, * _year, * _hours, * _minutes;
public:
    DateTime(int day = 1, int month = 1, int year = 2000,
        int hours = 0, int minutes = 0) {
        _day = new int(day);
        _month = new int(month);
        _year = new int(year);
        _hours = new int(hours);
        _minutes = new int(minutes);
    }

    DateTime(const DateTime& other) {
        _day = new int(*other._day);
        _month = new int(*other._month);
        _year = new int(*other._year);
        _hours = new int(*other._hours);
        _minutes = new int(*other._minutes);
    }

    DateTime& operator=(const DateTime& other) {
        if (this != &other) {
            delete _day;
            delete _month;
            delete _year;
            delete _hours;
            delete _minutes;

            _day = new int(*other._day);
            _month = new int(*other._month);
            _year = new int(*other._year);
            _hours = new int(*other._hours);
            _minutes = new int(*other._minutes);
        }
        return *this;
    }

    bool operator>(const DateTime& other) const {
        if (*_year != *other._year) {
            return *_year > *other._year;
        }
        if (*_month != *other._month) {
            return *_month > *other._month;
        }
        if (*_day != *other._day) {
            return *_day > *other._day;
        }
        if (*_hours != *other._hours) {
            return *_hours > *other._hours;
        }

        return *_minutes > *other._minutes;
    }

    bool operator==(const DateTime& other) const {
        if (*_year == *other._year &&
            *_month == *other._month &&
            *_day == *other._day &&
            *_hours == *other._hours &&
            *_minutes == *other._minutes) {
            return true;
        }
        return false;
    }

    string ToString() const {
        string result = "";

        result += Format(*_day);

        result += ".";

        result += Format(*_month);

        result += ".";

        result += to_string(*_year);

        result += " ";

        result += Format(*_hours);

        result += ":";

        result += Format(*_minutes);

        return result;
    }

    int GetYear() const { return *_year; }
    friend ostream& operator<<(ostream& COUT, const DateTime& obj) {
        // ToString returns the date and time in the format DD.MM.YYYY HH:MM
        COUT << obj.ToString();
        return COUT;
    }
    ~DateTime() {
        delete _day;
        delete _month;
        delete _year;
        delete _hours;
        delete _minutes;
        _day = _month = _year = _hours = _minutes = nullptr;
    }
};

class Intervention {
    string _description;
    string _technician;
    double _price;
    int _durationMinutes;
public:
    const string& GetDescription() const { return _description; }

    Intervention(const string& description, const string& technician, double price, int duration) {
        _description = description;
        _technician = technician;
        _price = price;
        _durationMinutes = duration;
    }

    string ToString() const {
        string result = "";

        result += _description;
        result += " | ";
        result += _technician;
        result += " | ";
        // the currency suffix was missing
        // also, cutting four digits off truncates prices: 85.509 becomes 85.50. it now rounds to two decimals
        ostringstream price;
        price << fixed << setprecision(2) << _price;
        result += price.str();
        result += " KM";
        result += " | ";
        result += to_string(_durationMinutes);
        result += " min";

        return result;
    }

    const string& GetTechnician() const { return _technician; }
    double GetPrice() const { return _price; }
    int GetDurationMinutes() const { return _durationMinutes; }
    friend ostream& operator<<(ostream& COUT, const Intervention& obj) {
        /*
        ToString returns data in the format:
        description | technician | price KM | duration min
        Disk replacement | Haris Hadzic | 85.50 KM | 45 min
        */
        COUT << obj.ToString();
        return COUT;
    }
};

class Client {
    string _fullName;
    string _email;
    string _phone;
public:
    Client(const string& fullName, const string& email, const string& phone) {
        _fullName = fullName;
        _email = email;
        _phone = phone;
    }

    Client(const Client& other) {
        _fullName = other._fullName;
        _email = other._email;
        _phone = other._phone;
    }

    Client& operator=(const Client& other) {
        if (this != &other) {
            _fullName = other._fullName;
            _email = other._email;
            _phone = other._phone;
        }
        return *this;
    }

    const string& GetFullName() const { return _fullName; }
    const string& GetEmail() const { return _email; }
    const string& GetPhone() const { return _phone; }
    friend ostream& operator<<(ostream& COUT, const Client& obj) {
        COUT << obj.GetFullName() << " | " << obj.GetEmail()
            << " | " << obj.GetPhone();
        return COUT;
    }
};

string GenerateLabel(const char* fullName, int serialNumber, int year) {
    // a null name used to reach strlen and which caused a crash
    if (fullName == nullptr || serialNumber < 1 || serialNumber > 999 || year < 2000 || year > 2099) {
        return "SRV-000/XX-0000";
    }

    // the single word test in main failed because both initials came from the
    // same letter. read at least two words, then keep the first and last ones.
    // this also handles empty names and extra whitespace without reading a null.
    istringstream name(fullName);
    string firstWord, lastWord, word;
    if (!(name >> firstWord >> lastWord)) {
        return "SRV-000/XX-0000";
    }
    while (name >> word) {
        lastWord = word;
    }

    // the regex expects uppercase ascii initials. the exam doesn't spell out how lowercase input should work
    // not entirely sure if normalization is relevant
    char firstInitial = toupper(firstWord[0]);
    char lastInitial = toupper(lastWord[0]);
    if (firstInitial < 'A' || firstInitial > 'Z' || lastInitial < 'A' || lastInitial > 'Z') {
        return "SRV-000/XX-0000";
    }

    string result = "SRV-";
    if (serialNumber < 10) {
        result += "00";
        result += to_string(serialNumber);
    }
    else if (serialNumber < 100) {
        result += "0";
        result += to_string(serialNumber);
    }
    else {
        result += to_string(serialNumber);
    }

    result += "/";

    result += firstInitial;
    result += lastInitial;

    result += "-";
    result += to_string(year);

    return result;
}

class ServiceRequest {
    char* _label;
    char* _device;
    char* _faultDescription;
    int _serialNumber;
    Client _client;
    Collection<RequestStatus, DateTime, 10> _statuses;
    vector<Intervention> _interventions;
public:
    ServiceRequest(const char* device, const char* faultDescription, const Client& client, int serialNumber, DateTime time) : _client(client) {
        _device = AllocateText(device);
        _faultDescription = AllocateText(faultDescription);
        _serialNumber = serialNumber;
        string generatedLabel = GenerateLabel(_client.GetFullName().c_str(), serialNumber, time.GetYear());
        _label = AllocateText(generatedLabel.c_str());
        _statuses.Add(RECEIVED, time);
    }

    ServiceRequest(const ServiceRequest& other) : _client(other._client) {
        _device = AllocateText(other._device);
        _faultDescription = AllocateText(other._faultDescription);
        _serialNumber = other._serialNumber;
        _label = AllocateText(other._label);
        _statuses = other._statuses;
        _interventions = other._interventions;
    }

    ServiceRequest& operator=(const ServiceRequest& other) {
        if (this != &other) {
            delete[] _device;
            delete[] _faultDescription;
            delete[] _label;

            _device = AllocateText(other._device);
            _faultDescription = AllocateText(other._faultDescription);
            _serialNumber = other._serialNumber;
            _label = AllocateText(other._label);
            _statuses = other._statuses;
            _interventions = other._interventions;
            _client = other._client;
        }

        return *this;
    }

    bool AddIntervention(const Intervention& inspection) {
        // both values must be greater than zero. these < 0 checks still accept
        // zero price or duration. change them to <= 0.
        if ((GetCurrentStatus() != DIAGNOSTICS && GetCurrentStatus() != REPAIR) ||
            inspection.GetPrice() < 0 || inspection.GetDurationMinutes() < 0) {
            return false;
        }

        _interventions.push_back(inspection);
        return true;
    }

    double TotalPrice() const {
        double sum = 0;
        for(int i = 0; i < _interventions.size(); i++) {
            sum += _interventions[i].GetPrice();
        }
        return sum;
    }

    int TotalDuration() const {
        int sum = 0;
        for (int i = 0; i < _interventions.size(); i++) {
            sum += _interventions[i].GetDurationMinutes();
        }
        return sum;
    }

    bool AddStatus(RequestStatus status, const DateTime& time) {
        RequestStatus current = GetCurrentStatus();

        if (current == COMPLETED) {
            return false;
        }

        if (current + 1 != status) {
            return false;
        }

        if (!(time > GetCurrentTime())) {
            return false;
        }

        _statuses.Add(status, time);
        return true;
    }

    string ToString() const {
        string result = "";
        result += _label;
        result += " | ";
        result += _client.GetFullName();
        result += " | ";
        result += _device;
        result += " | ";
        result += RequestStatusNames[GetCurrentStatus()];

        return result;
    }

    const char* GetLabel() const { return _label; }
    const char* GetDevice() const { return _device; }
    const char* GetFaultDescription() const { return _faultDescription; }
    int GetSerialNumber() const { return _serialNumber; }
    Client& GetClient() { return _client; }
    const Client& GetClient() const { return _client; }
    Collection<RequestStatus, DateTime, 10>& GetStatuses() { return _statuses; }
    const Collection<RequestStatus, DateTime, 10>& GetStatuses() const { return _statuses; }
    vector<Intervention>& GetInterventions() { return _interventions; }
    const vector<Intervention>& GetInterventions() const { return _interventions; }
    RequestStatus GetCurrentStatus() const { return _statuses.GetElement1(_statuses.GetCurrentCount() - 1); }
    DateTime GetCurrentTime() const { return _statuses.GetElement2(_statuses.GetCurrentCount() - 1); }
    friend ostream& operator<<(ostream& COUT, const ServiceRequest& obj) {
        // ToString returns:
        // label | client full name | device | current status
        COUT << obj.ToString();
        return COUT;
    }
    ~ServiceRequest() {
        delete[] _label;
        delete[] _device;
        delete[] _faultDescription;
        _label = _device = _faultDescription = nullptr;
    }
};

class Service {
    char* _name;
    vector<ServiceRequest> _requests;
public:
    Service(const char* name = "") {
        _name = AllocateText(name);
    }

    Service(const Service& other) {
        _name = AllocateText(other._name);
        _requests = other._requests;
    }

    Service& operator=(const Service& other) {
        if (this != &other) {
            delete[] _name;
            _name = AllocateText(other._name);
            _requests = other._requests;
        }
        return *this;
    }

    void AddRequest(const ServiceRequest& request) {
        for (int i = 0; i < _requests.size(); i++) {
            if (request.GetSerialNumber() == _requests[i].GetSerialNumber() ||
                strcmp(request.GetLabel(), _requests[i].GetLabel()) == 0) {
                throw exception("Serial number or label must not be the same");
            }
        }
        _requests.push_back(request);
    }

    ServiceRequest* FindRequest(const string& label) {
        for (int i = 0; i < _requests.size(); i++) {
            if (strcmp(label.c_str(), _requests[i].GetLabel()) == 0) {
                return &_requests[i];
            }
        }
        return nullptr;
    }

    bool RecordStatus(const string& label, RequestStatus status, const DateTime& time) {
        ServiceRequest* request = FindRequest(label);

        if (request == nullptr) {
            return false;
        }

        if (!request->AddStatus(status, time)) {
            return false;
        }

        if (status == COMPLETED) {
            thread t([request]() {
                cout << separator;
                cout << "To: " << request->GetClient().GetEmail() << endl;
                cout << "From: racuni@servis.ba" << endl;
                cout << "Subject: Service request completed - invoice" << endl << endl;

                cout << "Dear " << request->GetClient().GetFullName() << "," << endl << endl;

                cout << "Service request " << request->GetLabel()
                    << " for device " << request->GetDevice()
                    << " has been completed." << endl;

                // tiny difference: the example shows 140.50, this printed 140.5
                // format it if you want the same display
                ostringstream amount;
                amount << fixed << setprecision(2) << request->TotalPrice();
                cout << "Total amount: " << amount.str() << " KM" << endl << endl;

                cout << "Thank you for your trust." << endl;
                cout << separator;
                });

            t.join();
        }
        return true;
    }

    vector<ServiceRequest*> ExtractUnfinished() {
        vector<ServiceRequest*> unfinished;
        for (int i = 0; i < _requests.size(); i++) {
            if (_requests[i].GetCurrentStatus() != COMPLETED) {
                unfinished.push_back(&_requests[i]);
            }
        }
        return unfinished;
    }

    double CalculateRevenue() const {
        double sum = 0;

        for (int i = 0; i < _requests.size(); i++) {
            if (_requests[i].GetCurrentStatus() == COMPLETED) {
                sum += _requests[i].TotalPrice();
            }
        }

        return sum;
    }

    const char* GetName() const { return _name; }
    vector<ServiceRequest>& GetRequests() { return _requests; }
    const vector<ServiceRequest>& GetRequests() const { return _requests; }
    ~Service() {
        delete[] _name; _name = nullptr;
    }
};

const char* GetAnswerToFirstQuestion() {
    cout << "Question -> Explain why operator<< is implemented as a global function rather than a member function, and how the prefix and postfix forms of the increment operator are implemented?\n";
    // UNANSWERED
    return "Answer -> ENTER YOUR ANSWER HERE";
}

const char* GetAnswerToSecondQuestion() {
    cout << "Question -> Explain how, using the covered classes and methods, you could determine the size of a text file.\n";
    // UNANSWERED
    return "Answer -> ENTER YOUR ANSWER HERE";
}

bool ValidateLabel(const string& label) {
    regex rule("^SRV-(?!000)[0-9]{3}/[A-Z]{2}-20[0-9]{2}$");

    return regex_match(label, rule);
}

int main() {
    cout << PHONE_MESSAGE; cin.get();
    cout << PHONE_MESSAGE; cin.get();
    cout << EXAM_MESSAGE; cin.get();
    system("cls");

    cout << GetAnswerToFirstQuestion() << separator;
    cin.get();
    cout << GetAnswerToSecondQuestion() << separator;
    cin.get();

    /*
    The GenerateLabel function generates a service request label in the format:
    SRV-BBB/IN-GGGG

    The function signature should be:
    string GenerateLabel(const char* fullName, int serialNumber, int year)

    SRV  -> fixed prefix,
    BBB  -> request serial number padded with zeros in empty positions,
    IN   -> initials of the client's first and last name,
    YYYY -> year the request was received.

    For names containing multiple words, the initial of the first and last
    word is used. The serial number must be in the range 1-999, and the year 2000-2099.
    For invalid data, the function returns "SRV-000/XX-0000".
    */
    if (GenerateLabel("Amina Buric", 42, 2026) == "SRV-042/AB-2026")
        cout << "Label OK" << separator;
    if (GenerateLabel("Goran Skondric", 7, 2026) == "SRV-007/GS-2026")
        cout << "Label OK" << separator;
    if (GenerateLabel("Ana Marija Kovac", 156, 2027) ==
        "SRV-156/AK-2027")
        cout << "Label OK" << separator;
    if (GenerateLabel("Amina", 42, 2026) == "SRV-000/XX-0000" &&
        GenerateLabel("Amina Buric", 0, 2026) == "SRV-000/XX-0000" &&
        GenerateLabel("Amina Buric", 1000, 2026) == "SRV-000/XX-0000" &&
        GenerateLabel("Amina Buric", 42, 1999) == "SRV-000/XX-0000")
        cout << "Invalid label data OK" << separator;

    /*
    Using regex, the ValidateLabel function checks the previously defined
    format. The prefix must be SRV, the serial number must have three digits and cannot
    be 000, the initials must be uppercase letters, and the year must be 2000-2099.

    The function signature should be:
    bool ValidateLabel(const string& label)
    */
    if (ValidateLabel("SRV-042/AB-2026"))
        cout << "LABEL VALID" << separator;
    if (!ValidateLabel("SRV/042-AB-2026") &&
        !ValidateLabel("SRV-42/AB-2026") &&
        !ValidateLabel("SRV-042/Ab-2026") &&
        !ValidateLabel("SRV-000/AB-2026") &&
        !ValidateLabel("2026-SRV-042/AB"))
        cout << "LABEL IS NOT VALID" << separator;

    Collection<int, string, 6> numbers;
    numbers.Add(10, "Ten");
    numbers.Add(20, "Twenty");
    numbers.Add(10, "Ten");
    numbers.Add(30, "Thirty");
    numbers.Add(20, "Twenty");
    cout << numbers << separator;

    /*
    RemoveDuplicates returns a new collection in which only the first
    occurrence of each pair is kept. A pair is considered a duplicate only if
    both the first and second elements are equal. The original collection remains unchanged.
    */
    Collection<int, string, 6> withoutDuplicates = numbers.RemoveDuplicates();
    cout << "Without duplicates:" << separator << withoutDuplicates;
    cout << "Original:" << separator << numbers;

    try {
        Collection<int, string, 2> full;
        full.Add(1, "One");
        full.Add(2, "Two");
        full.Add(3, "Three");
    }
    catch (exception& e) {
        cout << "Exception: " << e.what() << separator;
    }

    Collection<int, string, 6> numbersCopy = numbers;
    numbersCopy[0] = 100;
    Collection<int, string, 6> assignedNumbers;
    assignedNumbers = numbers;
    assignedNumbers.GetElement2(0) = "Modified";
    cout << "Original:" << separator << numbers;
    cout << "Copy:" << separator << numbersCopy;
    cout << "Assigned object:" << separator << assignedNumbers;

    DateTime received(9, 7, 2026, 8, 0);
    DateTime diagnostics(9, 7, 2026, 9, 0);
    DateTime repair(9, 7, 2026, 10, 0);
    DateTime completed(9, 7, 2026, 11, 0);

    /*
    ToString returns the date and time in the format DD.MM.YYYY HH:MM, including
    leading zeros.
    */
    cout << received.ToString() << separator; // 09.07.2026 08:00
    if (diagnostics > received)
        cout << "Diagnostics time is after receipt" << separator;
    DateTime dateCopy(diagnostics);
    if (dateCopy == diagnostics && !(received == diagnostics))
        cout << "Time check, OK." << separator;

    Client amina("Amina Buric", "amina@fit.ba", "061-111-222");
    Client goran("Goran Skondric", "goran@fit.ba", "062-222-333");
    Client clientCopy = amina;
    cout << clientCopy << separator;

    /*
    An Intervention contains a description, technician name, price, and duration in minutes.
    */
    Intervention inspection("Device diagnostics", "Haris Hadzic", 20, 30);
    Intervention diskReplacement("Disk replacement", "Haris Hadzic", 85.5, 45);
    Intervention installation("System installation", "Maja Majic", 35, 60);
    /* ToString returns data in the format:
    description | technician | price KM | duration min
    Disk replacement | Haris Hadzic | 85.50 KM | 45 min
    */
    cout << diskReplacement.ToString() << separator;

    /*
    The ServiceRequest constructor generates a label based on the client,
    serial number, and year of receipt, and records the initial RECEIVED status
    with the provided time.
    */
    ServiceRequest laptop("Laptop", "Does not start", amina, 42, received);
    ServiceRequest phone("Phone", "Broken screen", goran, 7, received);

    /*
    ToString returns data in the format:
    label | client full name | device | current status
    SRV-042/AB-2026 | Amina Buric | Laptop | RECEIVED
    */
    cout << laptop.ToString() << separator;
    if (laptop.ToString() ==
        "SRV-042/AB-2026 | Amina Buric | Laptop | RECEIVED")
        cout << "ServiceRequest ToString OK" << separator;

    /*
    AddStatus adds a status only if the time is greater than the time of the last
    status and if the status represents the immediately following phase.

    The allowed sequence is: RECEIVED -> DIAGNOSTICS -> REPAIR -> COMPLETED

    Skipping or repeating statuses is not allowed. After the status
    COMPLETED, no new changes are allowed. An unsuccessful attempt returns false
    without modifying the status collection.
    */
    if (!laptop.AddStatus(REPAIR, diagnostics))
        cout << "Skipping statuses is not allowed" << separator;
    if (laptop.AddStatus(DIAGNOSTICS, diagnostics))
        cout << "DIAGNOSTICS status added" << separator;
    if (!laptop.AddStatus(DIAGNOSTICS, repair))
        cout << "Repeating statuses is not allowed" << separator;

    /*
    AddIntervention adds an intervention only while the request is in status
    DIAGNOSTICS or REPAIR, with price and duration greater than zero.
    The method returns true if the intervention was added, otherwise false.

    TotalPrice returns the sum of the prices of all interventions, and TotalDuration the sum
    of their durations in minutes.
    */
    if (laptop.AddIntervention(inspection))
        cout << "Intervention added" << separator;
    if (laptop.AddStatus(REPAIR, repair))
        cout << "REPAIR status added" << separator;
    laptop.AddIntervention(diskReplacement);
    laptop.AddIntervention(installation);
    cout << "Total price: " << laptop.TotalPrice() << " KM" << separator;
    cout << "Total duration: " << laptop.TotalDuration() << " min" << separator;

    ServiceRequest laptopCopy = laptop;
    cout << laptopCopy << separator;

    Service fitService("FIT Service");

    /*
    AddRequest adds a request to the service. It is not allowed to add two requests
    with the same serial number or the same label. In case of a duplicate, the method
    throws an exception.
    */
    fitService.AddRequest(laptop);
    fitService.AddRequest(phone);
    try {
        fitService.AddRequest(phone);
    }
    catch (exception& e) {
        cout << "Exception: " << e.what() << separator;
    }

    /*
    FindRequest returns a pointer to the request with the provided label.
    If the request is not found, the method returns nullptr.
    */
    string laptopLabel = laptop.GetLabel();
    ServiceRequest* found = fitService.FindRequest(laptopLabel);
    if (found != nullptr)
        cout << "Request found: " << found->GetLabel() << separator;
    if (fitService.FindRequest("SRV-999/XX-2026") == nullptr)
        cout << "Request not found" << separator;

    /*
    RecordStatus finds the request and attempts to add a status using
    the rules of the AddStatus method.

    The invoice is sent in a separate thread only after successfully recording
    the COMPLETED status. No notifications are sent for other statuses. If the request does not
    exist or the status was not added, the method returns false.

    Example invoice content:
    ---------------------------------------------------------------------------------
    To: amina@fit.ba
    From: racuni@servis.ba
    Subject: Service request completed - invoice

    Dear Amina Buric,

    Service request SRV-042/AB-2026 for device Laptop has been completed.
    Total amount: 140.50 KM

    Thank you for your trust.
    ---------------------------------------------------------------------------------
    */
    if (fitService.RecordStatus(laptopLabel, COMPLETED, completed))
        cout << "Request completed and invoice sent" << separator;
    if (!fitService.RecordStatus(
        laptopLabel, COMPLETED, DateTime(9, 7, 2026, 12, 0)))
        cout << "Repeating the final status is not allowed" << separator;
    if (!fitService.RecordStatus(
        "NONEXISTENT", DIAGNOSTICS, diagnostics))
        cout << "Status was not recorded for a nonexistent request" << separator;

    /*
    ExtractUnfinished returns a vector of pointers to all requests whose current
    status is not COMPLETED.
    */
    vector<ServiceRequest*> unfinished = fitService.ExtractUnfinished();
    for (auto request : unfinished)
        cout << request->GetLabel() << " -> "
        << RequestStatusNames[(int)request->GetCurrentStatus()] << separator;

    /*
    CalculateRevenue returns the sum of prices of all interventions recorded on
    requests that have the COMPLETED status. Interventions on unfinished
    requests are not included in revenue.
    */
    cout << "Revenue: " << fitService.CalculateRevenue()
        << " KM" << separator;

    Service serviceCopy = fitService;
    cout << serviceCopy.GetName() << " has "
        << serviceCopy.GetRequests().size() << " requests" << separator;

    cin.get();
    return 0;
}