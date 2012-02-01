# -*- coding: utf-8 -*-
# Copyright (C) 2011 Rosen Diankov <rosen.diankov@gmail.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from common_test_openrave import *

class TestTrajectory(EnvironmentSetup):
    def test_merging(self):
        env = self.env
        self.LoadEnv('robots/pr2-beta-static.zae')
        robot=env.GetRobots()[0]
        basemanip=interfaces.BaseManipulation(robot)
        manip1=robot.SetActiveManipulator('leftarm')
        Tgoal1 = manip1.GetTransform()
        Tgoal1[0,3] -= 0.3
        Tgoal1[2,3] += 0.4
        trajdata=basemanip.MoveToHandPosition(matrices=[Tgoal1],execute=False,outputtraj=True)
        traj1=RaveCreateTrajectory(env,'').deserialize(trajdata)

        manip2=robot.SetActiveManipulator('rightarm')
        Tgoal2 = manip2.GetTransform()
        Tgoal2[0,3] -= 0.5
        Tgoal2[1,3] -= 0.5
        Tgoal2[2,3] += 0.2
        trajdata=basemanip.MoveToHandPosition(matrices=[Tgoal2],execute=False,outputtraj=True)
        traj2=RaveCreateTrajectory(env,'').deserialize(trajdata)

        traj3=planningutils.MergeTrajectories([traj1,traj2])

        with robot:
            dofvalues=traj3.GetConfigurationSpecification().ExtractJointValues(traj3.GetWaypoint(-1),robot,range(robot.GetDOF()),0)
            robot.SetDOFValues(dofvalues)
            assert( transdist(manip1.GetTransform(),Tgoal1) <= g_epsilon)
            assert( transdist(manip2.GetTransform(),Tgoal2) <= g_epsilon)
            assert( abs(traj3.GetDuration() - max(traj1.GetDuration(),traj2.GetDuration())) <= g_epsilon )

    def test_grabbing(self):
        env = self.env
        with env:
            self.LoadEnv('robots/pr2-beta-static.zae')
            robot=env.GetRobots()[0]
            basemanip=interfaces.BaseManipulation(robot)
            manip1=robot.SetActiveManipulator('leftarm')
            Tgoal1 = manip1.GetTransform()
            Tgoal1[0,3] -= 0.3
            Tgoal1[2,3] += 0.4

        trajdata=basemanip.MoveToHandPosition(matrices=[Tgoal1],execute=False,outputtraj=True)
        traj1=RaveCreateTrajectory(env,'').deserialize(trajdata)
        
        with env:
            body1=env.ReadKinBodyURI('data/mug1.kinbody.xml')
            env.AddKinBody(body1,True)
            body1.SetTransform(manip1.GetTransform())
            
        newspec = traj1.GetConfigurationSpecification()
        newspec.AddGroup('grab %s %d'%(robot.GetName(),manip1.GetEndEffector().GetIndex()),1,'previous')
        graboffset = newspec.GetGroupFromName('grab').offset
        traj1grab = RaveCreateTrajectory(env,'')
        traj1grab.Init(newspec)
        data=traj1.GetWaypoints(0,traj1.GetNumWaypoints(),newspec)
        data[graboffset] = body1.GetEnvironmentId()
        data[-newspec.GetDOF()+graboffset] = -body1.GetEnvironmentId()
        traj1grab.Insert(0,data)

        # run the trajectory
        robot.GetController().SendCommand('SetThrowExceptions 1')
        env.StartSimulation(0.01,False)
        robot.GetController().SetPath(traj1grab)
        assert(robot.WaitForController(traj1grab.GetDuration()+1))
        assert(transdist(body1.GetTransform(),Tgoal1) <= g_epsilon )
        assert(len(robot.GetGrabbed())==0)

        # try with another arm
        with env:
            manip2=robot.SetActiveManipulator('rightarm')
            Tgoal2 = manip2.GetTransform()
            Tgoal2[0,3] -= 0.5
            Tgoal2[1,3] -= 0.5
            Tgoal2[2,3] += 0.2
            trajdata=basemanip.MoveToHandPosition(matrices=[Tgoal2],execute=False,outputtraj=True)
            traj2=RaveCreateTrajectory(env,'').deserialize(trajdata)

        with env:
            body2=env.ReadKinBodyURI('data/mug1.kinbody.xml')
            env.AddKinBody(body2,True)
            body2.SetTransform(manip2.GetTransform())

        newspec = traj2.GetConfigurationSpecification()
        newspec.AddGroup('grab %s %d'%(robot.GetName(),manip2.GetEndEffector().GetIndex()),1,'previous')
        graboffset = newspec.GetGroupFromName('grab').offset
        traj2grab = RaveCreateTrajectory(env,'')
        traj2grab.Init(newspec)
        data=traj2.GetWaypoints(0,traj2.GetNumWaypoints(),newspec)
        data[graboffset] = body2.GetEnvironmentId()
        data[-newspec.GetDOF()+graboffset] = -body2.GetEnvironmentId()
        traj2grab.Insert(0,data)
        
        traj3=planningutils.MergeTrajectories([traj1grab,traj2grab])

        # run the trajectory
        robot.GetController().SetPath(traj3)
        assert(robot.WaitForController(traj3.GetDuration()+1))
        assert(transdist(body1.GetTransform(),Tgoal1) <= g_epsilon )
        assert(transdist(body2.GetTransform(),Tgoal2) <= g_epsilon )
        assert(len(robot.GetGrabbed())==0)

    def test_grabonly(self):
        env = self.env
        with env:
            self.LoadEnv('robots/pr2-beta-static.zae')
            robot=env.GetRobots()[0]
            manip1=robot.SetActiveManipulator('leftarm')
            body1=env.ReadKinBodyURI('data/mug1.kinbody.xml')
            env.AddKinBody(body1,True)
            body1.SetTransform(manip1.GetTransform())

            robot.GetController().SendCommand('SetThrowExceptions 1')
            env.StartSimulation(0.01,False)

            spec=ConfigurationSpecification()
            spec.AddGroup('grab %s %d'%(robot.GetName(),robot.GetActiveManipulator().GetEndEffector().GetIndex()),1,'previous')
            spec.AddGroup('deltatime',1,'linear')
            traj=RaveCreateTrajectory(self.env,'')
            traj.Init(spec)
            traj.Insert(0,[body1.GetEnvironmentId(),0])

        robot.GetController().SetPath(traj)
        assert(robot.WaitForController(0.1))
        assert(robot.GetGrabbed()[-1] == body1)

    def test_smoothingsamepoint(self):
        env = self.env
        self.LoadEnv('data/lab1.env.xml')
        robot=env.GetRobots()[0]
        for delta in [1e-8,1e-9,1e-10,1e-11,1e-12,1e-13,1e-14,1e-15,1e-16]:
            traj = RaveCreateTrajectory(env,'')
            traj.Init(robot.GetActiveConfigurationSpecification())
            traj.Insert(0,robot.GetActiveDOFValues())
            traj.Insert(1,robot.GetActiveDOFValues()+delta*ones(robot.GetActiveDOF()))
            for plannername in ['parabolicsmoother','shortcut_linear']:
                planningutils.SmoothActiveDOFTrajectory(traj,robot,False,maxvelmult=1,plannername=plannername)
                planningutils.SmoothActiveDOFTrajectory(traj,robot,False,maxvelmult=1,plannername=plannername)
            for plannername in ['parabolictrajectoryretimer', 'lineartrajectoryretimer']:
                planningutils.RetimeActiveDOFTrajectory(traj,robot,False,maxvelmult=1,plannername=plannername)
                planningutils.RetimeActiveDOFTrajectory(traj,robot,False,maxvelmult=1,plannername=plannername)

    def test_simpleretiming(self):
        env=self.env
        env.Load('robots/barrettwam.robot.xml')
        robot=env.GetRobots()[0]
        robot.SetActiveDOFs(range(7))
        traj = RaveCreateTrajectory(env,'')
        traj.Init(robot.GetActiveConfigurationSpecification())
        traj.Insert(0,zeros(7))
        traj.Insert(1,numpy.minimum(0.5,robot.GetActiveDOFLimits()[1]))
        planningutils.RetimeActiveDOFTrajectory(traj,robot,False,maxvelmult=1,plannername='parabolictrajectoryretimer')
        parameters = Planner.PlannerParameters()
        parameters.SetRobotActiveJoints(robot)
        planningutils.VerifyTrajectory(parameters,traj,samplingstep=0.002)
        robot.GetController().SetPath(traj)
        while not robot.GetController().IsDone():
            env.StepSimulation(0.01)
            
    def test_smoothwithcircular(self):
        print 'test smoothing with circular joints'
        env=self.env
        self.LoadEnv('data/pa10calib.env.xml')
        robot=env.GetRobots()[0]
        traj=RaveCreateTrajectory(env,'')
        trajxml = """<trajectory>
<configuration>
<group name="joint_values PA10 0 1 2 3 4 5 6" offset="0" dof="7" interpolation="linear"/>
</configuration>

<data count="49">
0.6232796600868203 -0.8112710061292812 0.7999999999999998 0.6799631064508246 0.1091755354059138 1.440731827698615 2.922283401707198 0.6297659060914433 -0.791896844803094 0.8178285806447316 0.6926179013352842 0.08766435149958259 1.427920262546699 2.913468581341383 1.503972143656972 -0.9274864371467325 1.225573917311743 1.003437877648504 -0.4340282761288557 1.823200101638587 3.098016069378392 1.525185021612136 -0.9331519020556411 1.234868889346184 1.014691108733368 -0.4468302042491505 1.833329603939712 3.103930219009325 1.5463978995673 -0.9388173669645494 1.244163861380624 1.025944339818231 -0.4596321323694453 1.843459106240837 3.109844368640257 1.567610777522464 -0.9444828318734579 1.253458833415064 1.037197570903095 -0.4724340604897401 1.853588608541962 3.11575851827119 1.588823655477628 -0.9501482967823666 1.262753805449504 1.048450801987958 -0.4852359886100349 1.863718110843087 3.121672667902123 1.610036533432792 -0.955813761691275 1.272048777483944 1.059704033072821 -0.4980379167303295 1.873847613144212 3.127586817533055 1.631249411387956 -0.9614792266001836 1.281343749518385 1.070957264157685 -0.5108398448506243 1.883977115445337 3.133500967163988 1.65246228934312 -0.9671446915090921 1.290638721552825 1.082210495242548 -0.523641772970919 1.894106617746462 3.139415116794921 1.673675167298284 -0.9728101564180006 1.299933693587265 1.093463726327412 -0.5364437010912138 1.904236120047587 -3.137856040753733 1.694888045253446 -0.9784756213269096 1.309228665621706 1.104716957412276 -0.5492456292115089 1.914365622348711 3.151243416056785 1.768477491729069 -0.858623477800765 1.222218154809126 0.9641516389871772 -0.6920262133927459 1.904373843952331 3.255188040566058 1.778990269797015 -0.8415017430113158 1.209788081835901 0.944070879212163 -0.7124234397043513 1.902946447038562 3.270037272638811 1.789503047864962 -0.8243800082218665 1.197358008862675 0.9239901194371489 -0.7328206660159566 1.901519050124793 3.284886504711565 1.780997116546671 -0.8173747151353777 1.177261052644005 0.9223185059169084 -0.7400461535176325 1.897779926914885 -2.981038652082886 1.772491185228381 -0.810369422048889 1.157164096425336 0.9206468923966682 -0.747271641019308 1.894040803704977 -2.96377850169775 1.763985253910091 -0.8033641289624004 1.137067140206666 0.918975278876428 -0.7544971285209835 1.890301680495069 -2.946518351312615 1.755479322591801 -0.7963588358759117 1.116970183987996 0.9173036653561878 -0.7617226160226591 1.886562557285161 -2.929258200927479 1.74697339127351 -0.789353542789423 1.096873227769326 0.9156320518359472 -0.7689481035243347 1.882823434075253 -2.911998050542343 0.6667201138506444 0.1003186791946383 -1.455440212001736 0.7033371347654194 -1.686585016237153 1.407954786416909 -0.7199589516301085 0.6582141825323542 0.107323972281127 -1.475537168220406 0.7016655212451789 -1.693810503738829 1.404215663207 -0.7026988012449729 0.6497082512140638 0.1143292653676157 -1.495634124439075 0.6999939077249385 -1.701035991240505 1.400476539997092 -0.6854386508598372 0.6412023198957735 0.1213345584541043 -1.515731080657745 0.698322294204698 -1.70826147874218 1.396737416787184 -0.6681785004747015 0.6326963885774831 0.128339851540593 -1.535828036876415 0.696650680684458 -1.715486966243856 1.392998293577275 -0.6509183500895659 0.6241904572591926 0.1353451446270817 -1.555924993095084 0.6949790671642179 -1.722712453745532 1.389259170367367 -0.63365819970443 0.6156845259409023 0.1423504377135704 -1.576021949313754 0.6933074536439776 -1.729937941247208 1.385520047157459 -0.6163980493192943 0.6071785946226118 0.1493557308000591 -1.596118905532424 0.6916358401237372 -1.737163428748884 1.381780923947551 -0.5991378989341586 0.5986726633043216 0.1563610238865478 -1.616215861751093 0.689964226603497 -1.744388916250559 1.378041800737643 -0.581877748549023 0.5901667319860312 0.1633663169730365 -1.636312817969763 0.6882926130832564 -1.751614403752235 1.374302677527735 -0.5646175981638875 0.5816608006677335 0.1703716100595274 -1.656409774188434 0.6866209995630174 -1.75883989125391 1.370563554317825 5.735827859400842 -0.42814069596912 -0.4649467545775149 -1.751470087760962 0.03704785629781469 -1.778588776721555 0.625614420268662 5.15291743426412 -0.4158048805137168 -0.4872259586354415 -1.74684719374974 0.05051853910319864 -1.760254377573389 0.6055420435706921 5.156013190933851 -0.4174817282842055 -0.49483178664785 -1.72843953979616 0.05593516530178318 -1.740200278912081 0.6033089479882394 -1.142929810431415 -0.4191585760546943 -0.5024376146602585 -1.710031885842581 0.06135179150036778 -1.720146180250772 0.6010758524057866 -1.158687504617093 -0.4208354238251831 -0.5100434426726669 -1.691624231889002 0.06676841769895242 -1.700092081589464 0.598842756823334 -1.174445198802771 -0.4225122715956719 -0.5176492706850755 -1.673216577935423 0.07218504389753716 -1.680037982928156 0.5966096612408814 -1.190202892988449 -0.4241891193661606 -0.5252550986974842 -1.654808923981843 0.07760167009612177 -1.659983884266848 0.5943765656584287 -1.205960587174127 -0.543245311070862 -1.065268887578487 -0.3478654932777039 0.462182130195625 -0.2361428793139618 0.4358267793042803 -2.324756874357273 -0.5449221588413509 -1.072874715590896 -0.3294578393241245 0.4675987563942096 -0.2160887806526537 0.4335936837218275 -2.340514568542951 -0.5465990066118396 -1.080480543603304 -0.3110501853705449 0.4730153825927942 -0.1960346819913455 0.4313605881393751 -2.356272262728629 -0.5482758543823283 -1.088086371615713 -0.2926425314169657 0.4784320087913787 -0.1759805833300373 0.4291274925569223 -2.372029956914307 -0.5499527021528171 -1.095692199628121 -0.2742348774633862 0.4838486349899631 -0.1559264846687291 0.4268943969744696 -2.387787651099985 -0.5516295499233055 -1.10329802764053 -0.2558272235098042 0.4892652611885498 -0.1358723860074225 0.4246613013920161 3.879639961893922 -0.5486519599153192 -1.095411164822057 -0.2698588952376889 0.4764586768093309 -0.1095847329118121 0.4160472363161167 3.85957028218165 -0.545674369907333 -1.087524302003584 -0.2838905669655735 0.463652092430112 -0.08329707981620163 0.4074331712402174 3.839500602469378 -0.5426967798993466 -1.07963743918511 -0.2979222386934581 0.4508455080508931 -0.05700942672059117 0.398819106164318 3.819430922757106 -0.4306048612859366 -1.331235863773695 -0.6 0.9649208887187276 1.61258423001619 1.843347204006895 2.572631741801914 -0.4306048612859366 -1.331235863773695 -0.6 0.9649208887187276 1.61258423001619 1.843347204006895 2.572631741801914 </data>
<description>Not documented yet.</description>
</trajectory>
"""
        traj.deserialize(trajxml)
        with env:
            circularindices = [j.GetDOFIndex() for j in robot.GetJoints() if j.IsCircular(0)]
            assert(len(circularindices)>0)
            robot.SetActiveDOFs(circularindices)
            spec = robot.GetActiveConfigurationSpecification()
            parameters = Planner.PlannerParameters()
            parameters.SetRobotActiveJoints(robot)
            startconfig = traj.GetWaypoint(0,spec)
            endconfig = traj.GetWaypoint(-1,spec)
            # discontinuity happens between 47 and 48, double check
            data=traj.GetWaypoints(0,traj.GetNumWaypoints(),spec)
            disindices = flatnonzero(abs(data[1:]-data[0:-1])>1)
            disindex = disindices[0]
            assert(abs(traj.GetWaypoint(disindex,spec)-traj.GetWaypoint(disindex+1,spec)) > 4)
            plannernames = ['parabolictrajectoryretimer','lineartrajectoryretimer']
            for plannername in plannernames:
                print 'planner',plannername
                traj2 = RaveCreateTrajectory(env,traj.GetXMLId())
                traj2.Clone(traj,0)
                planningutils.RetimeActiveDOFTrajectory(traj2,robot,False,maxvelmult=1,plannername=plannername)
                assert(traj2.GetDuration()<20)
                with robot:
                    planningutils.VerifyTrajectory(parameters,traj2,samplingstep=0.002)
                assert(transdist(traj2.GetWaypoint(0,spec),startconfig) <= g_epsilon)
                assert(transdist(traj2.GetWaypoint(-1,spec),endconfig) <= g_epsilon)
                
                # make sure discontinuity is covered
                timespec = ConfigurationSpecification()
                timespec.AddGroup('deltatime',1,'linear')
                times = cumsum(traj2.GetWaypoints(0,traj2.GetNumWaypoints(),timespec))
                for i in range(0,len(times)-1):
                    v0 = traj2.Sample(times[i],spec)
                    v1 = traj2.Sample((times[i]+times[i+1])/2,spec)
                    v2 = traj2.Sample(times[i+1],spec)
                    # care about distance centered at 0, add/subtract midpoint
                    dist01 = fmod((v0-v1)+3*pi,2*pi)-pi
                    dist02 = fmod((v0-v2)+3*pi,2*pi)-pi
                    assert(all(abs(dist01)<=abs(dist02)))

                robot.GetController().SetPath(traj2)
                while not robot.GetController().IsDone():
                    env.StepSimulation(0.01)

    def test_affine_smoothing(self):
        env=self.env
        robot=self.LoadRobot('robots/barrettwam.robot.xml')
        robot.SetActiveDOFs([], DOFAffine.X | DOFAffine.Y |DOFAffine.RotationAxis, [0,0,1])
        traj=RaveCreateTrajectory(env,'')
        traj.Init(robot.GetActiveConfigurationSpecification())
        traj.Insert(0,[0,0,0,  1,0,0.7, 1,0,-5.58, 1,0,-3.2])
        traj2=RaveCreateTrajectory(env,'')
        traj2.Clone(traj,0)

        env.StartSimulation(0.01,False)
            
        for itraj in range(2):
            with env:
                T=robot.GetTransform()
                planningutils.RetimeAffineTrajectory(traj2,[2,2,1],[5,5,5],False,plannername='lineartrajectoryretimer')
                assert(transdist(robot.GetTransform(),T) <= g_epsilon)
                assert(traj2.GetNumWaypoints()==traj.GetNumWaypoints())
                for i in range(traj.GetNumWaypoints()):
                    waypoint0=traj.GetWaypoint(i,robot.GetActiveConfigurationSpecification())
                    waypoint1=traj2.GetWaypoint(i,robot.GetActiveConfigurationSpecification())
                    assert(transdist(waypoint0,waypoint1) <= g_epsilon)
            robot.GetController().SetPath(traj2)
            robot.WaitForController(0)

        plannernames = ['parabolicsmoother','shortcut_linear']
        for plannername in plannernames:
            traj2=RaveCreateTrajectory(env,'')
            traj2.Clone(traj,0)
            for itraj in range(2):
                with env:
                    T=robot.GetTransform()
                    planningutils.SmoothAffineTrajectory(traj2,[2,2,1],[5,5,5],False,plannername=plannername)
                    assert(transdist(robot.GetTransform(),T) <= g_epsilon)
                    for i in [0,-1]:
                        waypoint0=traj.GetWaypoint(i,robot.GetActiveConfigurationSpecification())
                        waypoint1=traj2.GetWaypoint(i,robot.GetActiveConfigurationSpecification())
                        assert(transdist(waypoint0,waypoint1) <= g_epsilon)
                robot.GetController().SetPath(traj2)
                robot.WaitForController(0)
