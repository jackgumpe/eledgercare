param([Parameter(Mandatory)][string]$Work,[Parameter(Mandatory)][string]$Result)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class Pixels45 {
    private static byte[] Read(Bitmap bmp) {
        var lockData = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        try {
            var data = new byte[lockData.Stride*bmp.Height];
            Marshal.Copy(lockData.Scan0, data, 0, data.Length);
            return data;
        } finally { bmp.UnlockBits(lockData); }
    }
    public static long[] Compare(string oldFile, string newFile) {
        using (var a = new Bitmap(oldFile))
        using (var b = new Bitmap(newFile)) {
            if(a.Size!=b.Size || a.Width%4!=0) throw new ArgumentException("image dimensions");
            var av=Read(a); var bv=Read(b);
            long count=0, total=0, max=0;
            for (int i=0; i<av.Length; i+=3) {
                int delta=0;
                for(int j=0;j<3;j++) {
                    int v=Math.Abs((int)av[i+j]-bv[i+j]);
                    delta=Math.Max(delta,v);total+=v;
                }
                if(delta>0) count++;
                max=Math.Max(max,delta);
            }
            return new long[]{count,total,max,a.Width,a.Height};
        }
    }
}
'@
$rows=@()
foreach($pair in @(@('I','Mathematical-Specification',11),@('II','Integrated-Concepts',11),@('III','Coordinator-Handoff',5))) {
    $roman=$pair[0]
    for($j=0;$j -lt ($pair[2]+5);$j++) {
        $full=Join-Path $Work ('complete-render/Targeted-Depth-{0}-Complete-02.1-{1:d2}.png' -f $roman,$j)
        if($j -lt 5) {
            $reference=Join-Path $Work ('public-render/Amendment-{0}-02.1-{1:d2}.png' -f $roman,$j)
        } else {
            $reference=Join-Path $Work ('original-render/Targeted-Depth-{0}-{1}-{2:d2}.png' -f $roman,$pair[1],($j-5))
        }
        $v=[Pixels45]::Compare($reference,$full)
        $rows+=([ordered]@{paper=$roman;physical_page=$j+1;different_pixels=$v[0];absolute_difference_sum_channels=$v[1];max_channel_difference=$v[2];width=$v[3];height=$v[4]})
    }
}
[IO.File]::WriteAllText($Result,(ConvertTo-Json -Depth 4 $rows).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rows | Where-Object {$_['different_pixels'] -gt 0} | ForEach-Object { $_ | ConvertTo-Json -Compress }
