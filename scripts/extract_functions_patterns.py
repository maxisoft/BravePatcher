import array
import base64
import datetime
import json
import os
import sys
import traceback

from __main__ import findBytes, getBytes, getCurrentProgram, getReferencesTo, getFunctionContaining, getFunctionBefore, \
    getInstructionAt, getInstructionContaining
from ghidra.program.model.address.Address import NO_ADDRESS

prog = getCurrentProgram()


def get_function_at(address):
    return getFunctionContaining(address) or getFunctionBefore(address)


def get_functions_containing_string_ref(s):
    addr = findBytes(prog.getMinAddress(), s)
    if addr is None or addr == NO_ADDRESS:
        raise ValueError("Unable to find the string: %s" % s)
    refs = getReferencesTo(addr)
    if len(refs) == 0:
        raise ValueError("There's no reference to the given string")
    for ref in refs:
        func = get_function_at(ref.getFromAddress())
        if func is None:
            raise ValueError("There's no function that point to the given string")
        yield func, ref


def get_function_containing_string_ref(s):
    ret = None
    for i, (func, _) in enumerate(get_functions_containing_string_ref(s)):
        if i:
            raise ValueError("There's more than 1 reference to the given string")
        else:
            ret = func
    if ret is None:
        raise ValueError("There's no reference to the given string")
    return ret


def get_and_mark_bool_function_using_string(s, name=None):
    func = get_function_containing_string_ref(s)
    if name:
        func.setName(name, ghidra.program.model.symbol.SourceType.USER_DEFINED)
    func.setReturn(ghidra.program.model.data.BooleanDataType.dataType,
                   func.getReturn().getVariableStorage(),
                   ghidra.program.model.symbol.SourceType.USER_DEFINED)

    return func


bool_funcs_by_string = {
    "NotificationHelperWin::ShouldShowNotifications": "Notification not made: Full screen mode",
    "NotificationHelperWin::IsNotificationsEnabled": "Failed to initialize toast notifier",
    "NotificationHelperWin::IsFocusAssistEnabled": "Failed to determine Focus Assist status",
    "NotificationHelperWin::InitializeToastNotifier": "Failed to create toast notifier",

    "AdsPerDayFrequencyCap::ShouldAllow": "You have exceeded the allowed ads per day",
    "AdsPerHourFrequencyCap::ShouldAllow": "You have exceeded the allowed ads per hour",
    "AllowNotificationsFrequencyCap::ShouldAllow": "Notifications not allowed",
    "BrowserIsActiveFrequencyCap::ShouldAllow": "Browser window is not active",
    "MediaFrequencyCap::ShouldAllow": "Media is playing",
    "DoNotDisturbFrequencyCap::ShouldAllow": "Should not disturb",
    "NetworkConnectionFrequencyCap::ShouldAllow": "Network connection is unavailable",
    "MinimumWaitTimeFrequencyCap::ShouldAllow": "Ad cannot be shown as minimum wait time has not passed",
    "NewTabPageAdsPerHourFrequencyCap::ShouldAllow": "You have exceeded the allowed new tab page ads per hour",
    "NewTabPageAdsPerDayFrequencyCap::ShouldAllow": "You have exceeded the allowed new tab page ads per day",
    "UnblindedTokensFrequencyCap::ShouldAllow": "You do not have enough unblinded tokens",
    # TODO UserActivityFrequencyCap

    "ads::ShouldAllow": "../../brave/vendor/bat-native-ads/src/bat/ads/internal/frequency_capping/permission_rules/permission_rule_util.",
    "ads:ShouldExclude": r"../../brave/vendor/bat-native-ads/src\\bat/ads/internal/frequency_capping/exclusion_rules/exclusion_rule_util.h",
    "AdPacing::ShouldPace": "Pacing ad delivery for creative instance id ",
}


def gen_pattern(address, limit=500):
    """Naive Function Pattern Generator.
    Extract the op codes in order
    """
    instr = getInstructionAt(address) or getInstructionContaining(address)
    ret = list()
    func = get_function_at(address)
    while instr and limit > 0:
        proto = instr.getPrototype()
        instr_len = proto.getLength()
        mask = proto.getInstructionMask()
        addr = instr.getInstructionContext().getAddress()
        out = getBytes(addr, instr_len)
        mask.applyMask(getBytes(addr, instr_len), out)
        original = array.array('B', getBytes(addr, instr_len).tostring())
        out = array.array('B', out.tostring())
        for i, v in enumerate(out):
            if (original[i] & 0xF) != (v & 0xF):
                out[i] &= 0xF0
            if (original[i] & 0xF0) != (v & 0xF0):
                out[i] &= 0x0F
        ret += out.tostring()
        next_instr = instr.getNext()
        next_addr = next_instr.getInstructionContext().getAddress()
        limit -= 1
        if get_function_at(next_addr) != func:
            break
        if next_addr.subtract(addr) > instr_len:
            # handle instructions gaps due to jump padding / alignment / protection (most likely 0xCC)
            ret += ('\xcc' for _ in range(next_addr.subtract(addr) - instr_len))
        instr = next_instr
    return ret


def format_pattern(pattern):
    def mapping(b):
        if b == '\xcc':  # skip int3 or instructions gaps
            return '??'
        s = hex(ord(b))[2:]
        return s.zfill(2).replace('0', '?')

    return " ".join(map(mapping, pattern))


def gen_pattern_payload(name):
    payload = dict()
    payload['id'] = name
    s = bool_funcs_by_string[name]
    func = get_and_mark_bool_function_using_string(s, name)
    payload['name'] = func.getName()
    payload['callingConvention'] = func.getCallingConventionName()
    payload['entryPoint'] = func.getEntryPoint().getUnsignedOffset()
    pattern = gen_pattern(func.getEntryPoint())
    payload['pattern'] = format_pattern(pattern)

    return payload


def export_data(data, start="0ad6e844f7be412295a884e6358cc1e7", end="0e5ba08f37754fd4b16df92028efc455"):
    extract_dir = os.environ.get("EXTRACT_DIRECTORY")
    if extract_dir:
        with open(os.path.join(extract_dir, "patterns_%s.json" % prog.getUniqueProgramID()), "w") as f:
            f.write(data)
    else:
        sys.stdout.write(start)
        sys.stdout.write(base64.b64encode(data))
        sys.stdout.write(end)
        sys.stdout.write('\n')
        sys.stdout.flush()


def search_for_MaybeDeliverAd():
    def find_test_then_call_instr(func, ref):
        instr = getInstructionAt(ref.getFromAddress()) or getInstructionContaining(ref.getFromAddress())
        addr = instr.getInstructionContext().getAddress()
        prev = instr
        while addr.subtract(func.getEntryPoint()) > 0:
            instr, prev = instr.getPrevious(), instr
            addr = instr.getInstructionContext().getAddress()
            if str(instr).startswith('CALL') and str(prev) == "TEST AL,AL":
                return instr.getOpObjects(0)[0]

    res = None
    for func, ref in get_functions_containing_string_ref("Ad notification not delivered"):
        target = find_test_then_call_instr(func, ref)
        if target:
            if res is not None:
                raise Exception("There's two possible target function")
            f = get_function_at(target)
            f.setName("AdServing::MaybeDeliverAd", ghidra.program.model.symbol.SourceType.USER_DEFINED)
            res = f
    if res is None:
        raise Exception("No MaybeDeliverAd() function found")

    res.setName("AdDelivery::MaybeDeliverAd", ghidra.program.model.symbol.SourceType.USER_DEFINED)
    return res


def extract_no_ShowNotification():
    func = search_for_MaybeDeliverAd()

    def get_last_call_instruction():
        addr = func.getEntryPoint()
        instr = getInstructionAt(addr) or getInstructionContaining(addr)
        call = None
        while get_function_at(instr.getInstructionContext().getAddress()) == func:
            if str(instr).startswith('CALL'):
                call = instr
            instr = instr.getNext()
        return call

    call_instr = get_last_call_instruction()
    assert call_instr
    f = get_function_at(call_instr.getOpObjects(0)[0])
    f.setName("AdDelivery::ShowNotification", ghidra.program.model.symbol.SourceType.USER_DEFINED)

    payload = dict()
    payload['id'] = "AdDelivery::ShowNotification"
    payload['name'] = f.getName()
    payload['callingConvention'] = f.getCallingConventionName()
    payload['entryPoint'] = f.getEntryPoint().getUnsignedOffset()
    pattern = gen_pattern(f.getEntryPoint())
    payload['pattern'] = format_pattern(pattern)

    return payload


def main():
    payload = dict()
    payload["version"] = "1"
    payload["date"] = datetime.datetime.utcnow().isoformat()
    program = dict()
    payload["program"] = program
    program["compiler"] = prog.getCompiler()
    program["creationDate"] = prog.getCreationDate().getTime()
    program["pointerSize"] = int(prog.getDefaultPointerSize())
    program["format"] = prog.getExecutableFormat()
    program["md5"] = prog.getExecutableMD5()
    program["path"] = prog.getExecutablePath()
    program["sha256"] = prog.getExecutableSHA256()
    program["id"] = prog.getUniqueProgramID()
    program["imageBase"] = prog.getImageBase().getUnsignedOffset()

    patterns = dict()
    payload["patterns"] = patterns
    payload["errors"] = list()
    for k, v in bool_funcs_by_string.items():
        try:
            patterns[k] = gen_pattern_payload(k)
        except Exception as e:
            payload["errors"].append([k, str(e)])
    try:
        patterns["AdDelivery::ShowNotification"] = extract_no_ShowNotification()
    except Exception as e:
        payload["errors"].append(["AdDelivery::ShowNotification", str(e)])
    print(json.dumps(payload))
    export_data(json.dumps(payload))


main()
