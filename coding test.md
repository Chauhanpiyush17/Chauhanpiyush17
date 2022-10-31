import cocotb
from cocotb.triggers import FallingEdge, RisingEdge
from cocotb.clock import Clock
from cocotb_bus.monitors import BusMonitor
from cocotb_bus.drivers import BusDriver
from cocotb.scoreboard import Scoreboard
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory

import logging
import random


class Scrambler():
    def __init__(self, dut, input_test=False):
        self.dut = dut
        self.input_test = input_test
        

        cocotb.fork(Clock(dut.CLK, 1, units="ns").start())

        self.input_stream = InPutDriv(dut)
        self.seed_stream = seedDriv(dut)

        self.input_stream_recv = InPutMntr(dut, callback=self.model)
        self.output_stream_recv = OutGetMntr(dut)
        self.intr_stream_recv = Intr_Mntr(dut, callback=self.intr_model)
        self.seed_stream_recv = seedMntr(dut, callback=self.seed_model)

        self.expected_output = []
        self.expected_intr = []
        self.received_transactions = []
        self.N = 0
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_stream_recv, self.expected_output)
        self.scoreboard.add_interface(self.intr_stream_recv, self.expected_intr)
        self.log = logging.getLogger("cocotb_tb_log")
        self.log.setLevel(logging.DEBUG)

    def seed_model(self, transaction):
        if (int.from_bytes(transaction[0].buff) == 0):
            self.N <= transaction[1].buff
            self.dut._log.info("seed Model")

   

    def model(self, transaction):
        self.log.debug("Transaction")
        self.received_transactions.append(transaction)
        self.pkts_sent += 1
        sum_model = BinaryValue(sum([int.from_bytes(i, byteorder='little') for i in self.received_transactions]),
                                n_bits=len(self.input_stream.bus.in_data), bigEndian=False)
        self.expected_output.append(sum_model)
        if (self.pkts_sent.value == self.N.value):
            self.log.debug("number of inputs required %d but received %d" % (self.N.value, self.pkts_sent))
        self.log.debug("Expected Output = %d" % self.expected_output.value)

    async def reset(self):
        self.log.debug("Resetting DUT")
        self.dut.RST_N.setimmediatevalue(0)
        self.dut.in_en.setimmediatevalue(0)
        self.dut.in_data.setimmediatevalue(0)
        self.dut.out_en.setimmediatevalue(0)
        self.dut.seed_en.setimmediatevalue(0)
        self.dut.seed_data.setimmediatevalue(0)
        await FallingEdge(self.dut.CLK)
        self.dut.RST_N <= 1


class InPutDriv(BusDriver):
    _signals = ["in_en", "in_data", "in_rdy"]

    def __init__(self, dut, callback=None):
        BusDriver.__init__(self, dut, dut.CLK)
        self.bus.in_data <= 0
        self.bus.in_en <= 0

    async def _driver_send(self, transaction, sync=True):
        await RisingEdge(self.clock)
        if self.bus.in_rdy:
            self.bus.in_data <= BinaryValue(transaction["data"], n_bits=len(self.bus.in_data), bigEndian=False)
            self.bus.in_en <= BinaryValue(transaction["enable"], n_bits=1, bigEndian=False)


class seedDriv(BusDriver):
    _signals = ["seed_en", "seed_data", "seed_rdy"]

    def __init__(self, dut, callback=None):
        BusDriver.__init__(self, dut, dut.CLK)
       
        self.bus.seed_data <= 0
        self.bus.seed_en <= 0

    async def _driver_send(self, transaction, sync=True):
        await RisingEdge(self.clock)
        if self.bus.seed_rdy:
          
            self.bus.seed_en <= BinaryValue(transaction["seed_en"], n_bits=1, bigEndian=False)
            self.bus.seed_data <= BinaryValue(transaction["seed_data"], n_bits=len(self.bus.seed_data),
                                                   bigEndian=False)


class InPutMntr(BusMonitor):
    _signals = ["in_rdy", "in_en", "in_data"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self, dut,dut.CLK)

    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.in_en.value == 1 and self.bus.in_rdy.value == 1:
            self._recv(self.bus.in_data.value)


class OutGetMntr(BusMonitor):
    _signals = ["out_rdy", "out_en", "out_data"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self, dut, dut.CLK)

    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.out_en.value == 1 and self.bus.out_rdy.value == 1:
            self._recv(self.bus.out_data.value)


class seedMntr(BusMonitor):
    _signals = ["seed_rdy", "seed_en", "seed_data"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self, dut, dut.CLK)

    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.seed_rdy.value == 1 and self.bus.seed_en.value == 1:
            self._recv( self.bus.seed_data.value)


class Intr_Mntr(BusMonitor):
    _signals = ["RDY_interrupt", "interrupt"]

    def __init__(self, dut, callback=None):
        BusMonitor.__init__(self, dut, "", dut.CLK)

    async def _monitor_recv(self):
        await RisingEdge(self.clock)
        if self.bus.RDY_interrupt.value:
            if self.bus.interrupt == 1:
                self._recv(self.bus.interrupt.value)


async def test_sum_n(dut, N=4, input_test=False):
    tb = Scrambler(dut, input_test)
    await tb.reset()
    exp_sum = 0
    seed_N = {"seed_en": 1, "seed_address": 0, "seed_data": N}
 
        seed_start = {"seed_en": 1, "seed_address": 1, "seed_data": 1}
    seed_end = {"seed_en": 0, "seed_address": 1, "seed_data": 1}
    await tb.seed_stream.send(seed_N)
    await tb.seed_stream.send(seed_start)
    await tb.seed_stream.send(seed_end)
    pkts_recvd = 0
    # test_data = [random.randint(0,2**8-1)for i in range(N)]
    test_data = [5, 4, 2, 1]
    if input_test is True:
        for i in range(N - 1):
            in_data_data = {"enable": 1, "data": test_data[i]}
            await tb.input_stream.send(in_data_data)
            pkts_recvd += 1
            exp_sum += test_data[i]
        dut._log.info('Required inputs %d but received %d. Interrupt value = %d' % (N, pkts_recvd, dut.interrupt.value))
   
    else:
        for i in range(N):
            in_data_data = {"enable": 1, "data": test_data[i]}
            await tb.input_stream.send(in_data_data)
            exp_sum += test_data[i]
        dut._log.info("Interrupt Value = %d" % dut.interrupt.value)

 
    dut.out_en <= 0
    await RisingEdge(dut.CLK)
    raise tb.scoreboard.result


tf = TestFactory(test_sum_n)
tf.add_option(('input_test'), ([False, False], [False, True], [True, False]))
tf.generate_tests()
