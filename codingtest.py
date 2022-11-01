# use cocotb framework
import cocotb
#use timer to model verilog like delays
import random
from cocotb.triggers import Timer
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge 
#use reporting machanism
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue

# input are - clk RST_N, in_en seed_en, out_en;
# bus input in_data, seed_data;
#output - seed_rdy, in_rdy, out_rdy
#output bus - out_data


#start test
@cocotb.test()
async def test(dut):
    dut.log.info("Start of test.....")
    #random.seed(6)
    RST_N = (1)
    seed_data = (6)
    seed_en = (1)
    in_data = (10)
    in_en = (0)
    out_en = (0)
    #vec = BinaryValue(12)
    #vec.integer = 12
    out_data =(BinaryValue(11))  
    seed_rdy = (1)
    in_rdy = (1) 
    out_rdy = (0)
    
    clock = Clock(dut.CLK, 100, 'sec')
    cocotb.fork(clock.start())
    for i in range (0):
         dut.RST_N.value = RST_N[i]
         dut.seed_data.value = seed_data[i] 
         dut.seed_en.value = seed_en[i]
         dut.in_data.value = in_data[i] 
         dut.in_en.value = in_en[i]
         dut.out_en.value =  out_en[i] 
         await FallingEdge(dut.CLK)
         await Timer(250,'sec')
         print('-------------------------------------------')
         print(type(dut.out_data.value))
         print('-------------------------------------------')
         assert dut.out_data.value == out_data[i], f"error"
         assert dut.seed_rdy.value == seed_rdy[i], f"error"
         assert dut.in_rdy.value == in_rdy[i], f"error"
         assert dut.out_rdy.value == out_rdy[i], f"error"
pass
