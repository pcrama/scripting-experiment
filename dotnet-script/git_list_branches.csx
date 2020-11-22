#!/usr/bin/env dotnet-script
#r "nuget: LibGit2Sharp, 0.26.2"
// https://edi.wang/post/2019/3/26/operate-git-with-net-core

using LibGit2Sharp;

using (var repo = new Repository(@"c:\Projects\MessageConfigurator\P_MessageConfigurator"))
{
    var branches = repo.Branches;
    foreach (var b in branches)
    {
        Console.WriteLine(b.FriendlyName);
    }
}
